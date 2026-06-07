import logging
from typing import Dict, Any, Tuple
from app.models.domain import Mandate, Portfolio, RiskEvent, Trade, MarketSensitivityScore
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.services import audit_service
from fastapi import BackgroundTasks
from app.core.sockets import manager

logger = logging.getLogger("nexa.risk_engine")

class RiskRejectionError(Exception):
    pass

class RiskEngine:
    def __init__(self, db_session: Session, background_tasks: BackgroundTasks = None):
        self.db = db_session
        self.background_tasks = background_tasks

    def evaluate_pre_trade(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        checks = [
            ("kill_switch", self._check_kill_switch),
            # ("asset_whitelist", self._check_asset_whitelist), # This check is not fully implemented in the mandate model yet
            ("drawdown_limit", self._check_drawdown_limit),
            ("daily_loss_limit", self._check_daily_loss_limit),
            ("leverage_limit", self._check_leverage_limit),            
            ("stop_loss_attached", self._check_stop_loss_attached),
            ("market_sentiment", self._check_market_sentiment),
        ]

        for check_name, check_func in checks:
            try:
                result = check_func(portfolio, mandate, order)
                if not result:
                    logger.warning(f"Risk check '{check_name}' returned False but no exception")
            except RiskRejectionError as e:
                logger.warning(f"Risk rejection on '{check_name}': {str(e)}")
                self._log_risk_event(portfolio, f"RISK_CHECK_FAILED: {check_name}", str(e), "WARNING")
                raise

        return True

    def _check_kill_switch(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if mandate.kill_switch_active:
            raise RiskRejectionError("System halted: Kill switch active.")
        return True

    def _check_drawdown_limit(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        # This is a simplified check. A real system would calculate this based on high-water mark.
        if portfolio.current_drawdown_pct and portfolio.current_drawdown_pct >= mandate.max_drawdown_pct:
            self._trigger_kill_switch(mandate, f"Max drawdown {portfolio.current_drawdown_pct:.2f}% >= limit {mandate.max_drawdown_pct:.2f}%")
            raise RiskRejectionError(f"Drawdown limit breached: {portfolio.current_drawdown_pct:.2f}% >= {mandate.max_drawdown_pct:.2f}%")
        return True

    def _check_daily_loss_limit(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_pnl = self.db.query(func.sum(
            Trade.pnl
        )).filter(
            Trade.portfolio_id == portfolio.pk_id,
            Trade.created_at >= today_start,
            Trade.status == "CLOSED"
        ).scalar() or 0

        daily_loss_limit_amount = portfolio.total_equity * (mandate.daily_loss_limit_pct / 100)
        if today_pnl < -daily_loss_limit_amount:
            self._trigger_kill_switch(mandate, f"Daily loss limit breached: PNL of ${today_pnl:,.2f} exceeds limit of ${-daily_loss_limit_amount:,.2f}")
            raise RiskRejectionError(f"Daily loss limit breached: PNL of ${today_pnl:,.2f} exceeds limit of ${-daily_loss_limit_amount:,.2f}")
        return True

    def _check_leverage_limit(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        notional_value = order['size'] * order['current_price']
        required_margin = notional_value / mandate.max_leverage

        if required_margin > portfolio.available_margin:
            raise RiskRejectionError(f"Leverage exceeded: Required ${required_margin:,.2f}, Available ${portfolio.available_margin:,.2f}")
        return True

    def _check_stop_loss_attached(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if 'stop_loss' not in order or order['stop_loss'] is None:
            raise RiskRejectionError("Trade must have a stop loss attached")
        return True

    def _check_market_sentiment(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        # Only block BUY orders if the AI is extremely bearish. We don't want to stop users from selling/cutting losses!
        if order.get('side') == 'BUY':
            symbol = order.get('symbol')
            sentiment = self.db.query(MarketSensitivityScore).filter(
                MarketSensitivityScore.symbol == symbol
            ).order_by(MarketSensitivityScore.timestamp.desc()).first()
            
            if sentiment and sentiment.score <= -0.5:
                raise RiskRejectionError(f"AI Sentiment is extremely bearish (Score: {sentiment.score}) for {symbol}. BUY orders are temporarily blocked to protect capital.")
                
        return True

    def _trigger_kill_switch(self, mandate: Mandate, reason: str):
        mandate.kill_switch_active = True
        self.db.commit()
        logger.critical(f"KILL SWITCH ENGAGED: {reason}")
        
        audit_service.create_audit_log(
            self.db,
            action_type="KILL_SWITCH_TRIGGERED",
            description=f"System halted for mandate {mandate.id}: {reason}",
            metadata_json={"mandate_id": mandate.id, "reason": reason}
        )
        self.db.commit() # Force commit before the exception rolls back the session
        
        if self.background_tasks:
            self.background_tasks.add_task(
                manager.broadcast,
                {"type": "RISK_ALERT", "data": {"severity": "CRITICAL", "event_type": "KILL_SWITCH_TRIGGERED", "description": reason, "triggered_at": datetime.utcnow().isoformat()}},
                "alerts"
            )

    def _log_risk_event(self, portfolio: Portfolio, event_type: str, description: str, severity: str = "WARNING"):
        event = RiskEvent(
            portfolio_id=portfolio.pk_id,
            event_type=event_type,
            severity=severity,
            description=description
        )
        self.db.add(event)
        self.db.commit()

        if self.background_tasks:
            self.background_tasks.add_task(
                manager.broadcast,
                {"type": "RISK_ALERT", "data": {"severity": severity, "event_type": event_type, "description": description, "triggered_at": datetime.utcnow().isoformat()}},
                "alerts"
            )

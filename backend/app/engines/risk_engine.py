import logging
from typing import Dict, Any, Tuple
from app.models.domain import Mandate, Portfolio, RiskEvent, Trade
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger("nexa.risk_engine")

class RiskRejectionError(Exception):
    pass

class RiskEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def evaluate_pre_trade(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        checks = [
            ("kill_switch", self._check_kill_switch),
            ("mandate_active", self._check_mandate_active),
            ("asset_whitelist", self._check_asset_whitelist),
            ("drawdown_limit", self._check_drawdown_limit),
            ("daily_loss_limit", self._check_daily_loss_limit),
            ("weekly_loss_limit", self._check_weekly_loss_limit),
            ("leverage_limit", self._check_leverage_limit),            
            ("position_size", self._check_position_size),
            ("total_exposure", self._check_total_exposure),
            ("stale_data", self._check_stale_data),
            ("stop_loss_attached", self._check_stop_loss_attached),
            ("trade_frequency", self._check_trade_frequency),
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

    def _check_mandate_active(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if not mandate:
            raise RiskRejectionError("Portfolio mandate is not defined.")
        return True

    def _check_asset_whitelist(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if "ALL" not in mandate.allowed_assets and order['symbol'] not in mandate.allowed_assets:
            raise RiskRejectionError(f"Asset {order['symbol']} not in whitelist: {mandate.allowed_assets}")
        return True

    def _check_drawdown_limit(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if portfolio.current_drawdown_pct >= mandate.max_drawdown_pct:
            self._trigger_kill_switch(mandate, f"Max Drawdown Exceeded: {portfolio.current_drawdown_pct}% >= {mandate.max_drawdown_pct}%")
            raise RiskRejectionError(f"Drawdown limit breached: {portfolio.current_drawdown_pct}% >= {mandate.max_drawdown_pct}%")
        return True

    def _check_daily_loss_limit(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_pnl = self.db.query(func.sum(
            Trade.pnl
        )).filter(
            Trade.portfolio_id == portfolio.id,
            Trade.created_at >= today_start,
            Trade.status == "CLOSED"
        ).scalar() or 0

        daily_loss_limit_amount = portfolio.total_equity * (mandate.daily_loss_limit_pct / 100)
        if today_pnl < -daily_loss_limit_amount:
            self._trigger_kill_switch(mandate, f"Daily Loss Limit Breached: {today_pnl} <= {-daily_loss_limit_amount}")
            raise RiskRejectionError(f"Daily loss limit breached: {today_pnl} <= {-daily_loss_limit_amount}")
        return True

    def _check_weekly_loss_limit(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if not mandate.weekly_loss_limit_pct:
            return True # Skip if not defined on mandate
        
        week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        weekly_pnl = self.db.query(func.sum(
            Trade.pnl
        )).filter(
            Trade.portfolio_id == portfolio.id,
            Trade.created_at >= week_start,
            Trade.status == "CLOSED"
        ).scalar() or 0

        weekly_loss_limit_amount = portfolio.total_equity * (mandate.weekly_loss_limit_pct / 100)
        if weekly_pnl < -weekly_loss_limit_amount:
            self._trigger_kill_switch(mandate, f"Weekly Loss Limit Breached: {weekly_pnl} <= {-weekly_loss_limit_amount}")
            raise RiskRejectionError(f"Weekly loss limit breached: {weekly_pnl} <= {-weekly_loss_limit_amount}")
        return True

    def _check_leverage_limit(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        notional_value = order['size'] * order['current_price']
        required_margin = notional_value / mandate.max_leverage

        if required_margin > portfolio.available_margin:
            raise RiskRejectionError(f"Leverage exceeded: Required ${required_margin:,.2f}, Available ${portfolio.available_margin:,.2f}")
        return True

    def _check_position_size(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if not mandate.max_position_size_pct:
            return True # Skip if not defined
            
        notional_value = order['size'] * order['current_price']
        max_position_notional = portfolio.total_equity * (mandate.max_position_size_pct / 100)

        if notional_value > max_position_notional:
            raise RiskRejectionError(f"Position size too large: ${notional_value:,.2f} > ${max_position_notional:,.2f} ({mandate.max_position_size_pct}%)")
        return True

    def _check_total_exposure(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        # This is a simplified check. A real one would be more complex.
        # It assumes total exposure is capped by total equity * max_leverage.
        open_trades = self.db.query(Trade).filter(
            Trade.portfolio_id == portfolio.id,
            Trade.status == "OPEN"
        ).all()
        
        current_exposure = sum(trade.size * trade.entry_price for trade in open_trades)
        new_trade_exposure = order['size'] * order['current_price']
        total_exposure = current_exposure + new_trade_exposure
        
        max_exposure = portfolio.total_equity * mandate.max_leverage

        if total_exposure > max_exposure:
             raise RiskRejectionError(f"Total exposure limit exceeded: Current ${current_exposure:,.2f} + New ${new_trade_exposure:,.2f} > Max ${max_exposure:,.2f}")
        return True

    def _check_stale_data(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if 'timestamp' in order:
            age_seconds = (datetime.utcnow() - order['timestamp']).total_seconds()
            if age_seconds > 300:  # Data older than 5 minutes
                self._trigger_kill_switch(mandate, f"Stale Market Data Detected: {age_seconds}s old")
                raise RiskRejectionError(f"Market data stale: {age_seconds}s old. Kill switch engaged.")
        return True

    def _check_stop_loss_attached(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if 'stop_loss' not in order or order['stop_loss'] is None:
            raise RiskRejectionError("Trade must have a stop loss attached")
        return True

    def _check_trade_frequency(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if not mandate.max_trade_frequency_per_hour:
            return True # Skip if not defined

        last_hour_trades = self.db.query(Trade).filter(
            Trade.portfolio_id == portfolio.id,
            Trade.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).count()

        if last_hour_trades > mandate.max_trade_frequency_per_hour:
            raise RiskRejectionError(f"Trade frequency exceeded: {last_hour_trades} trades in last hour (limit: {mandate.max_trade_frequency_per_hour})")
        return True

    def _trigger_kill_switch(self, mandate: Mandate, reason: str):
        mandate.kill_switch_active = True
        self.db.commit()
        logger.critical(f"KILL SWITCH ENGAGED: {reason}")

    def _log_risk_event(self, portfolio: Portfolio, event_type: str, description: str, severity: str = "WARNING"):
        event = RiskEvent(
            portfolio_id=portfolio.id,
            event_type=event_type,
            severity=severity,
            description=description
        )
        self.db.add(event)
        self.db.commit()

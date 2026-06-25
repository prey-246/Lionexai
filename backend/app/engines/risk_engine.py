import logging
from typing import Dict, Any, Tuple
from app.models.domain import (
    Mandate, Portfolio, RiskEvent, Trade, MarketSensitivityScore, GlobalSettings,
    GlobalMarketState,
)
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
            ("asset_whitelist", self._check_asset_whitelist),
            ("position_size", self._check_position_size),
            ("max_open_positions", self._check_max_open_positions),
            ("portfolio_exposure", self._check_portfolio_exposure),
            ("drawdown_limit", self._check_drawdown_limit),
            ("daily_loss_limit", self._check_daily_loss_limit),
            ("leverage_limit", self._check_leverage_limit),
            ("stop_loss_attached", self._check_stop_loss_attached),
            ("market_sentiment", self._check_market_sentiment),
            ("macro_regime", self._check_macro_regime),
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
        global_settings = self.db.query(GlobalSettings).filter_by(id="default").first()
        if global_settings and global_settings.global_kill_switch_active:
            raise RiskRejectionError("System halted: Global Kill Switch is active.")
            
        if mandate.kill_switch_active:
            raise RiskRejectionError("System halted: Kill switch active.")
        return True

    def _allowed_assets(self, mandate: Mandate):
        allowed = mandate.allowed_assets
        if isinstance(allowed, dict):
            allowed = allowed.get("symbols", [])
        return allowed or []

    def _open_exposure(self, portfolio: Portfolio, symbol: str | None = None) -> float:
        q = self.db.query(Trade).filter(
            Trade.portfolio_id == portfolio.pk_id,
            Trade.status == "OPEN",
        )
        if symbol:
            q = q.filter(Trade.symbol == symbol)
        return sum((t.quantity or 0) * (t.entry_price or 0) for t in q.all())

    def _check_asset_whitelist(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        # Whitelist only restricts opening/increasing risk; exits are always allowed.
        if order.get("side") != "BUY":
            return True
        allowed = self._allowed_assets(mandate)
        if not allowed or "ALL" in allowed:
            return True
        if order.get("symbol") not in allowed:
            raise RiskRejectionError(
                f"Asset {order.get('symbol')} is not in the mandate's allowed asset universe."
            )
        return True

    def _check_position_size(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if order.get("side") != "BUY" or not portfolio.total_equity:
            return True
        new_notional = order["size"] * order["current_price"]
        existing = self._open_exposure(portfolio, order.get("symbol"))
        position_pct = (existing + new_notional) / portfolio.total_equity * 100.0
        if position_pct > mandate.max_position_size_pct:
            raise RiskRejectionError(
                f"Position size {position_pct:.1f}% exceeds mandate limit "
                f"{mandate.max_position_size_pct:.1f}% for {order.get('symbol')}."
            )
        return True

    def _check_max_open_positions(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if order.get("side") != "BUY":
            return True
        open_symbols = {
            t.symbol for t in self.db.query(Trade).filter(
                Trade.portfolio_id == portfolio.pk_id, Trade.status == "OPEN"
            ).all()
        }
        if order.get("symbol") in open_symbols:
            return True  # increasing an existing position doesn't add a new slot
        if len(open_symbols) >= (mandate.max_open_positions or 9999):
            raise RiskRejectionError(
                f"Max open positions ({mandate.max_open_positions}) reached; cannot open {order.get('symbol')}."
            )
        return True

    def _check_portfolio_exposure(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        if order.get("side") != "BUY" or not portfolio.total_equity:
            return True
        new_notional = order["size"] * order["current_price"]
        total_exposure = self._open_exposure(portfolio) + new_notional
        exposure_pct = total_exposure / portfolio.total_equity * 100.0
        if exposure_pct > mandate.max_portfolio_exposure_pct:
            raise RiskRejectionError(
                f"Portfolio exposure {exposure_pct:.1f}% exceeds mandate limit "
                f"{mandate.max_portfolio_exposure_pct:.1f}%."
            )
        return True

    def _check_macro_regime(self, portfolio: Portfolio, mandate: Mandate, order: Dict[str, Any]) -> bool:
        # Halt new risk during a crisis regime; exits remain allowed.
        if order.get("side") != "BUY":
            return True
        state = self.db.query(GlobalMarketState).order_by(GlobalMarketState.computed_at.desc()).first()
        if state and state.market_regime == "CRISIS":
            raise RiskRejectionError(
                "Global market regime is CRISIS; new risk-taking is temporarily halted to protect capital."
            )
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
        if order.get('side') != 'BUY':
            return True

        symbol = order.get('symbol')
        global_settings = self.db.query(GlobalSettings).filter_by(id="default").first()
        threshold = global_settings.extreme_bearish_threshold if global_settings else -0.5

        sentiment = self.db.query(MarketSensitivityScore).filter(
            MarketSensitivityScore.symbol == symbol
        ).order_by(MarketSensitivityScore.timestamp.desc()).first()

        if sentiment and sentiment.score <= threshold:
            raise RiskRejectionError(
                f"AI Sentiment is extremely bearish (Score: {sentiment.score}) for {symbol}. "
                "BUY orders are temporarily blocked to protect capital."
            )

        # Gold/metals: block BUY in extreme volatility (crisis regime)
        if symbol in ("XAUUSD", "XAGUSD"):
            from app.models import domain as dom
            crisis = self.db.query(dom.MarketRegime).filter(
                dom.MarketRegime.scope == symbol,
                dom.MarketRegime.regime == "CRISIS",
            ).order_by(dom.MarketRegime.detected_at.desc()).first()
            if crisis:
                raise RiskRejectionError(f"Extreme volatility regime for {symbol}; new BUY orders blocked.")

        # Crypto: reduce leverage during global panic
        global_risk = self.db.query(MarketSensitivityScore).filter(
            MarketSensitivityScore.symbol == "GLOBAL_RISK"
        ).order_by(MarketSensitivityScore.timestamp.desc()).first()
        if global_risk and global_risk.score <= threshold:
            from app.models import domain as dom
            asset = self.db.query(dom.Asset).filter(dom.Asset.symbol == symbol).first() if symbol else None
            if asset and asset.asset_class == "CRYPTO":
                lev = order.get("leverage") or mandate.max_leverage or 1.0
                if lev > 1.0:
                    raise RiskRejectionError("Global risk-off: crypto leverage reduced; high-leverage BUY blocked.")

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

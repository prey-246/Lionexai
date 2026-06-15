import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.engines.risk_engine import RiskEngine, RiskRejectionError
from app.models import domain
from app.services import audit_service

logger = logging.getLogger(__name__)
router = APIRouter()


class StressTestResult(BaseModel):
    scenario_id: str
    passed: bool
    rejection_reason: str
    action_type: str
    audit_log_id: str | None
    description: str
    metadata_json: dict


SCENARIO_MAP = {
    "SCENARIO_A": "leverage",
    "SCENARIO_B": "ai_sentiment",
    "SCENARIO_C": "mandate_kill_switch",
    "SCENARIO_D": "global_kill_switch",
    "SCENARIO_E": "daily_loss",
}


@router.post(
    "/{scenario_id}/run",
    response_model=StressTestResult,
    dependencies=[Depends(require_role(["admin", "risk_manager"]))],
)
def run_stress_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    scenario_key = SCENARIO_MAP.get(scenario_id)
    if not scenario_key:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {scenario_id}")

    portfolio = db.query(domain.Portfolio).first()
    if not portfolio:
        raise HTTPException(status_code=400, detail="No portfolio available for stress test.")

    mandate = db.query(domain.Mandate).filter(domain.Mandate.pk_id == portfolio.mandate_pk_id).first()
    if not mandate:
        raise HTTPException(status_code=400, detail="Portfolio mandate not found.")

    global_settings = db.query(domain.GlobalSettings).filter_by(id="default").first()
    if not global_settings:
        global_settings = domain.GlobalSettings(id="default")
        db.add(global_settings)
        db.commit()
    original_global_kill = global_settings.global_kill_switch_active if global_settings else False
    original_mandate_kill = mandate.kill_switch_active
    original_drawdown = portfolio.current_drawdown_pct

    risk_engine = RiskEngine(db)
    rejection_reason = ""
    action_type = "RISK_REJECTION"
    passed = False
    metadata: dict = {"scenario_id": scenario_id, "portfolio_id": portfolio.id}

    try:
        if scenario_key == "leverage":
            order = {
                "symbol": "BTC/USDT",
                "size": 10.0,
                "current_price": 65000.0,
                "side": "BUY",
                "stop_loss": 60000.0,
            }
            metadata.update(order)
            try:
                risk_engine.evaluate_pre_trade(portfolio, mandate, order)
                rejection_reason = "Expected leverage rejection did not occur."
            except RiskRejectionError as e:
                rejection_reason = str(e)
                passed = "leverage" in rejection_reason.lower()
                action_type = "ORDER_REJECTED" if passed else "RISK_REJECTION"

        elif scenario_key == "ai_sentiment":
            db.add(domain.MarketSensitivityScore(
                symbol="ETH/USDT",
                score=-0.85,
                timestamp=datetime.utcnow(),
            ))
            db.commit()
            order = {
                "symbol": "ETH/USDT",
                "size": 1.0,
                "current_price": 3500.0,
                "side": "BUY",
                "stop_loss": 3300.0,
            }
            metadata.update(order)
            try:
                risk_engine.evaluate_pre_trade(portfolio, mandate, order)
                rejection_reason = "Expected AI sentiment rejection did not occur."
            except RiskRejectionError as e:
                rejection_reason = str(e)
                passed = "bearish" in rejection_reason.lower() or "sentiment" in rejection_reason.lower()

        elif scenario_key == "mandate_kill_switch":
            mandate.kill_switch_active = True
            db.commit()
            order = {
                "symbol": "BTC/USDT",
                "size": 0.01,
                "current_price": 65000.0,
                "side": "BUY",
                "stop_loss": 60000.0,
            }
            try:
                risk_engine.evaluate_pre_trade(portfolio, mandate, order)
                rejection_reason = "Expected mandate kill switch rejection did not occur."
            except RiskRejectionError as e:
                rejection_reason = str(e)
                passed = "kill switch" in rejection_reason.lower()

        elif scenario_key == "global_kill_switch":
            if global_settings:
                global_settings.global_kill_switch_active = True
                db.commit()
            order = {
                "symbol": "BTC/USDT",
                "size": 0.01,
                "current_price": 65000.0,
                "side": "BUY",
                "stop_loss": 60000.0,
            }
            try:
                risk_engine.evaluate_pre_trade(portfolio, mandate, order)
                rejection_reason = "Expected global kill switch rejection did not occur."
            except RiskRejectionError as e:
                rejection_reason = str(e)
                passed = "global kill switch" in rejection_reason.lower()
                action_type = "ORDER_REJECTED"

        elif scenario_key == "daily_loss":
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            daily_limit = portfolio.total_equity * (mandate.daily_loss_limit_pct / 100)
            db.add(domain.Trade(
                id=f"trd_{uuid.uuid4().hex[:12]}",
                portfolio_id=portfolio.pk_id,
                symbol="BTC/USDT",
                side="SELL",
                quantity=0.01,
                entry_price=65000.0,
                status="CLOSED",
                pnl=-(daily_limit + 1000),
                created_at=today_start + timedelta(hours=1),
                closed_at=today_start + timedelta(hours=1),
            ))
            db.commit()
            order = {
                "symbol": "BTC/USDT",
                "size": 0.01,
                "current_price": 65000.0,
                "side": "BUY",
                "stop_loss": 60000.0,
            }
            try:
                risk_engine.evaluate_pre_trade(portfolio, mandate, order)
                rejection_reason = "Expected daily loss rejection did not occur."
            except RiskRejectionError as e:
                rejection_reason = str(e)
                passed = "daily loss" in rejection_reason.lower()
                action_type = "KILL_SWITCH_TRIGGERED" if mandate.kill_switch_active else "ORDER_REJECTED"

        metadata["rejection_reason"] = rejection_reason
        metadata["passed"] = passed

        audit_log = audit_service.create_audit_log(
            db,
            action_type=action_type if passed else "STRESS_TEST_FAILED",
            description=rejection_reason if passed else f"Stress test failed: {rejection_reason}",
            metadata_json=metadata,
            user_id=current_user.id,
        )
        db.commit()

        return StressTestResult(
            scenario_id=scenario_id,
            passed=passed,
            rejection_reason=rejection_reason,
            action_type=action_type if passed else "STRESS_TEST_FAILED",
            audit_log_id=audit_log.id if audit_log else None,
            description=rejection_reason,
            metadata_json=metadata,
        )

    finally:
        portfolio.current_drawdown_pct = original_drawdown
        mandate.kill_switch_active = original_mandate_kill
        if global_settings:
            global_settings.global_kill_switch_active = original_global_kill
        db.commit()

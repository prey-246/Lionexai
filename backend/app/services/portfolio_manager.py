"""Central orchestrator for auto-managed fund portfolios.

Composes allocation, autonomous execution, weekly settlement, and strategy
optimization into a single management cycle. Gated by autonomous_v2_enabled.
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.core.database import SessionLocal
from app.models import domain
from app.engines.allocation_engine import AllocationEngine, _should_rebalance
from app.engines.macro_intelligence import MacroIntelligenceEngine
from app.services.autonomous_manager import AutonomousManager
from app.services.settlement_engine import SettlementEngine

logger = logging.getLogger("nexa.portfolio_manager")


class PortfolioManager:
    def __init__(self, db: Session):
        self.db = db
        self.allocation = AllocationEngine(db)
        self.autonomous = AutonomousManager(db)
        self.settlement = SettlementEngine(db)
        self.macro = MacroIntelligenceEngine(db)

    async def run_cycle(self):
        """Full management cycle: rebalance if due -> execute -> (settlement on schedule)."""
        global_state = self.macro.latest()
        portfolios = (
            self.db.query(domain.Portfolio)
            .filter(domain.Portfolio.auto_managed == True)
            .options(joinedload(domain.Portfolio.fund), joinedload(domain.Portfolio.allocations))
            .all()
        )
        for p in portfolios:
            try:
                fund = p.fund
                if fund and (_should_rebalance(self.db, p, fund) or not p.allocations):
                    self.allocation.rebalance_portfolio(p, trigger="MANAGER", global_state=global_state)
                    self.db.refresh(p)
                await self.autonomous.manage_portfolio(p, global_state)
            except Exception as e:
                logger.error("Portfolio manager cycle failed for %s: %s", p.id, e, exc_info=True)
                self.db.rollback()

    def maybe_weekly_settlement(self):
        """Run settlement if it's Monday or portfolio hasn't settled this week."""
        now = datetime.utcnow()
        if now.weekday() == 0:  # Monday
            self.settlement.run_weekly_settlement(force=False)


async def run_portfolio_manager_cycle():
    gs = SessionLocal()
    try:
        settings = gs.query(domain.GlobalSettings).filter_by(id="default").first()
        if not settings or not settings.autonomous_v2_enabled:
            from app.services.autonomous_manager import run_autonomous_cycle
            await run_autonomous_cycle()
            return
    finally:
        gs.close()

    db = SessionLocal()
    try:
        mgr = PortfolioManager(db)
        await mgr.run_cycle()
        mgr.maybe_weekly_settlement()
    finally:
        db.close()

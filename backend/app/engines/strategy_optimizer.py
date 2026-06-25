"""Weekly strategy scoring for self-optimizing allocation."""
import logging
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import domain

logger = logging.getLogger("nexa.strategy_optimizer")


def _zscore(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    arr = np.array(values, dtype=float)
    std = arr.std()
    if std < 1e-9:
        return [0.0] * len(values)
    return ((arr - arr.mean()) / std).tolist()


class StrategyOptimizer:
    def __init__(self, db: Session):
        self.db = db

    def score_strategy(self, strategy: domain.Strategy, days: int = 30) -> dict:
        name = strategy.name
        cutoff = datetime.utcnow() - timedelta(days=days)
        trades = (
            self.db.query(domain.Trade)
            .filter(domain.Trade.strategy_name == name, domain.Trade.status == "CLOSED", domain.Trade.created_at >= cutoff)
            .all()
        )
        if not trades:
            return {"sharpe": 0, "win_rate": 0, "max_drawdown": 0, "profit_factor": 0, "composite_score": 0}

        pnls = [t.pnl or 0 for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]
        win_rate = len(wins) / len(pnls) * 100 if pnls else 0
        gross_profit = sum(wins)
        gross_loss = sum(losses) or 1e-9
        profit_factor = gross_profit / gross_loss
        std = np.std(pnls) if len(pnls) > 1 else 1e-9
        sharpe = (np.mean(pnls) / std) * np.sqrt(252) if std > 1e-9 else 0
        cum = np.cumsum(pnls)
        peak = np.maximum.accumulate(cum)
        dd = (cum - peak)
        max_dd = abs(float(dd.min())) if len(dd) else 0

        return {
            "sharpe": round(float(sharpe), 4),
            "win_rate": round(win_rate, 2),
            "max_drawdown": round(max_dd, 4),
            "profit_factor": round(profit_factor, 4),
        }

    def run_weekly(self, period: str = "30D") -> int:
        strategies = self.db.query(domain.Strategy).all()
        rows = []
        for s in strategies:
            metrics = self.score_strategy(s)
            rows.append((s, metrics))

        if not rows:
            return 0

        sharpes = [r[1]["sharpe"] for r in rows]
        win_rates = [r[1]["win_rate"] for r in rows]
        pfs = [r[1]["profit_factor"] for r in rows]
        dds = [r[1]["max_drawdown"] for r in rows]
        z_sh = _zscore(sharpes)
        z_wr = _zscore(win_rates)
        z_pf = _zscore(pfs)
        z_dd = _zscore(dds)

        scored = []
        for i, (s, m) in enumerate(rows):
            composite = z_sh[i] + z_wr[i] + z_pf[i] - z_dd[i]
            scored.append((s, m, composite))
        scored.sort(key=lambda x: x[2], reverse=True)

        for rank, (s, m, composite) in enumerate(scored, start=1):
            self.db.add(domain.StrategyScore(
                strategy_pk_id=s.pk_id,
                strategy_name=s.name,
                period=period,
                sharpe=m["sharpe"],
                win_rate=m["win_rate"],
                max_drawdown=m["max_drawdown"],
                profit_factor=m["profit_factor"],
                composite_score=round(composite, 4),
                rank=rank,
            ))
        self.db.commit()
        logger.info("Strategy optimizer scored %d strategies.", len(scored))
        return len(scored)


def run_strategy_optimizer():
    db = SessionLocal()
    try:
        StrategyOptimizer(db).run_weekly()
    except Exception as e:
        logger.error("Strategy optimizer failed: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()

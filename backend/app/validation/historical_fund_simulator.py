"""Fund-level historical backtest using market_bars and allocation-engine logic.

Simulates multi-asset fund NAV with periodic rebalancing on real OHLCV data.
Results are stored in validated_fund_runs — never written to demo equity_curves.
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field, asdict, asdict
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session, joinedload

from app.analytics import performance_engine as pe
from app.engines.macro_intelligence import SAFE_HAVENS
from app.engines.regime_engine import _annualized_vol, classify_series
from app.engines.regime_engine_v2 import classify_series_v2, DEFAULT_ENSEMBLE_WEIGHTS
from app.engines.portfolio_constructors import build_weights, apply_regime_multipliers
from app.validation.strategy_overlay import overlay_multipliers, score_strategies_weekly
from app.models import domain
from app.services import market_data_service

logger = logging.getLogger("nexa.historical_fund_simulator")

VOL_FLOOR = 0.05
MOMENTUM_K = 2.0
REBALANCE_BAND_PCT = 2.0
COMMISSION_PCT = 0.10
SLIPPAGE_PCT = 0.10
DEFAULT_BAR_LIMIT = 2000
MIN_BARS = 60
MIN_OPTIMIZATION_BARS = 756  # ~3 years aligned daily panel


@dataclass
class SimulationConfig:
    """Override fund defaults for optimization experiments."""
    method: str | None = None
    rebalance_freq_days: int | None = None
    rebalance_mode: str = "calendar"  # calendar | regime_change | both
    cash_floor_pct: float | None = None
    max_assets: int | None = None
    symbols: list[str] | None = None
    vol_target_pct: float | None = None
    strategy_overlay: dict[str, float] | None = None
    use_regime_v2: bool = False
    use_ensemble: bool = False
    drift_band_pct: float = REBALANCE_BAND_PCT
    regime_cash_escalation: bool = True
    experiment_type: str = "BASELINE"
    experiment_label: str | None = None
    validation_type: str = "BACKTEST"
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_cache", None)
        return d


@dataclass
class FundBacktestResult:
    run_id: str
    fund_id: str
    validation_type: str
    period_start: datetime | None
    period_end: datetime | None
    initial_capital: float
    metrics: dict[str, Any] = field(default_factory=dict)
    equity_curve: list[dict] = field(default_factory=list)
    rebalance_log: list[dict] = field(default_factory=list)
    allocation_policy_snapshot: dict[str, Any] = field(default_factory=dict)
    experiment_config: dict[str, Any] = field(default_factory=dict)
    rank_score: float | None = None
    data_coverage: dict[str, Any] = field(default_factory=dict)
    data_source: str = "HISTORICAL_MARKET_BARS"
    provenance: str = "VALIDATED_HISTORICAL"

    def to_dict(self) -> dict:
        return asdict(self)


def _sanitize_weights(weights: dict[str, float]) -> dict[str, float]:
    clean: dict[str, float] = {}
    for sym, wt in (weights or {}).items():
        try:
            val = float(wt)
            clean[sym] = 0.0 if math.isnan(val) or math.isinf(val) else round(val, 4)
        except (TypeError, ValueError):
            clean[sym] = 0.0
    return clean


def _global_state_from_panel(panel: pd.DataFrame, idx: int) -> tuple[str, str]:
    """Derive market regime and risk-on/off from BTC or first liquid symbol at index idx."""
    proxy = "BTC/USDT" if "BTC/USDT" in panel.columns else panel.columns[0]
    slice_df = panel.iloc[: idx + 1][[proxy]].dropna()
    if len(slice_df) < 30:
        return "SIDEWAYS", "NEUTRAL"
    ohlcv = pd.DataFrame({
        "close": slice_df[proxy].astype(float),
        "timestamp": slice_df.index,
    })
    result = classify_series(ohlcv)
    regime = result.regime
    if regime == "CRISIS":
        risk = "RISK_OFF"
    elif regime == "BULL":
        risk = "RISK_ON"
    else:
        risk = "NEUTRAL"
    return regime, risk


def _asset_signal_at(close_series: pd.Series) -> dict[str, float] | None:
    if close_series is None or len(close_series) < 20:
        return None
    close = close_series.astype(float)
    returns = close.pct_change()
    vol = max(_annualized_vol(returns), VOL_FLOOR)
    mom_window = min(63, len(close) - 1)
    momentum = (
        float(close.iloc[-1] / close.iloc[-1 - mom_window] - 1.0)
        if len(close) > mom_window
        else 0.0
    )
    return {"vol": vol, "momentum": momentum, "inv_vol": 1.0 / vol}


def _compute_targets(
    fund: domain.Fund,
    panel: pd.DataFrame,
    idx: int,
    symbols: list[str],
    max_position_cap: float,
    config: SimulationConfig | None = None,
    last_regime: str | None = None,
) -> dict[str, Any]:
    """Stateless allocation-engine logic at simulation date index."""
    policy = fund.allocation_policy or {}
    cfg = config or SimulationConfig()
    method = cfg.method or policy.get("method", "inverse_vol")
    base_cash_floor = float(cfg.cash_floor_pct if cfg.cash_floor_pct is not None else policy.get("cash_floor_pct", 10.0))
    max_assets = int(cfg.max_assets if cfg.max_assets is not None else policy.get("max_assets", 8))

    proxy = "BTC/USDT" if "BTC/USDT" in panel.columns else panel.columns[0]
    slice_df = panel.iloc[: idx + 1][[proxy]].dropna()
    if cfg.use_regime_v2 and len(slice_df) >= 30:
        ohlcv = pd.DataFrame({"close": slice_df[proxy].astype(float), "timestamp": slice_df.index})
        rv2 = classify_series_v2(ohlcv)
        regime = rv2.base_regime
        regime_v2 = rv2.regime
    else:
        regime, _ = _global_state_from_panel(panel, idx)
        regime_v2 = regime

    _, risk_on_off = _global_state_from_panel(panel, idx)

    cash_floor = base_cash_floor
    if cfg.regime_cash_escalation:
        if risk_on_off == "RISK_OFF":
            cash_floor += 15.0
        if regime == "CRISIS":
            cash_floor = max(cash_floor, 60.0)
    cash_floor = max(0.0, min(95.0, cash_floor))
    invested_pct = 100.0 - cash_floor

    fau_map = {fau.asset.symbol: fau for fau in fund.asset_universe if fau.asset}
    caps = {sym: min(max_position_cap, fau_map[sym].max_weight_pct) for sym in symbols if sym in fau_map}

    weights = build_weights(method, panel, idx, symbols, invested_pct, caps, max_assets)

    asset_regimes: dict[str, str] = {}
    for sym in weights:
        close_hist = panel[sym].iloc[: idx + 1].dropna()
        ohlcv = pd.DataFrame({"close": close_hist.astype(float), "timestamp": close_hist.index})
        asset_regimes[sym] = classify_series(ohlcv).regime

    weights = apply_regime_multipliers(weights, asset_regimes, regime, risk_on_off, set(SAFE_HAVENS))

    strategy_weights = cfg.strategy_overlay
    if cfg.use_ensemble and not strategy_weights:
        week_bucket = idx // 7
        if week_bucket in cfg._cache:
            strategy_weights = cfg._cache[week_bucket]
        else:
            weekly_scores = score_strategies_weekly(panel, idx, symbols)
            prior = DEFAULT_ENSEMBLE_WEIGHTS.get(regime_v2, DEFAULT_ENSEMBLE_WEIGHTS.get("SIDEWAYS", {}))
            strategy_weights = {
                k: 0.5 * weekly_scores.get(k, 0) + 0.5 * prior.get(k, 0)
                for k in set(list(weekly_scores.keys()) + list(prior.keys()))
            }
            total_sw = sum(strategy_weights.values()) or 1.0
            strategy_weights = {k: v / total_sw for k, v in strategy_weights.items()}
            cfg._cache[week_bucket] = strategy_weights

    if strategy_weights:
        mult = overlay_multipliers(panel, idx, list(weights.keys()), strategy_weights)
        weights = {s: round(weights[s] * mult.get(s, 1.0), 4) for s in weights}
        tot = sum(weights.values())
        if tot > 0:
            scale = invested_pct / tot
            weights = {s: round(v * scale, 4) for s, v in weights.items()}

    if cfg.vol_target_pct and idx >= 21:
        port_rets = panel[list(weights.keys())].iloc[: idx + 1].pct_change().dropna()
        if len(port_rets) >= 10:
            w_vec = np.array([weights.get(s, 0) / 100.0 for s in port_rets.columns])
            port_vol = float((port_rets.values @ w_vec).std() * np.sqrt(252) * 100)
            if port_vol > cfg.vol_target_pct:
                scale = cfg.vol_target_pct / port_vol
                weights = {s: round(v * scale, 4) for s, v in weights.items()}

    allocated = sum(weights.values())
    cash_pct = round(100.0 - allocated, 4)
    return {
        "cash_pct": cash_pct,
        "weights": _sanitize_weights(weights),
        "regime": regime,
        "regime_v2": regime_v2,
        "risk_on_off": risk_on_off,
    }


class HistoricalFundSimulator:
    """Replay fund allocation policy on historical market_bars."""

    def __init__(self, db: Session):
        self.db = db

    def run_fund_backtest(
        self,
        fund_id: str,
        initial_capital: float = 1_000_000.0,
        bar_limit: int = DEFAULT_BAR_LIMIT,
        validation_type: str = "BACKTEST",
        config: SimulationConfig | None = None,
        min_aligned_bars: int = MIN_BARS,
    ) -> FundBacktestResult:
        fund = (
            self.db.query(domain.Fund)
            .options(joinedload(domain.Fund.asset_universe).joinedload(domain.FundAssetUniverse.asset))
            .filter(domain.Fund.id == fund_id.upper())
            .first()
        )
        if not fund:
            raise ValueError(f"Fund not found: {fund_id}")

        cfg = config or SimulationConfig()
        if cfg.validation_type:
            validation_type = cfg.validation_type

        symbols = cfg.symbols or [
            fau.asset.symbol
            for fau in fund.asset_universe
            if fau.asset and fau.asset.is_active
        ]
        if not symbols:
            raise ValueError(f"No active assets in fund universe for {fund_id}")

        panel, coverage = market_data_service.get_bars_panel(
            self.db, symbols, limit=bar_limit, min_bars=MIN_BARS,
        )
        if panel.empty or len(panel) < min_aligned_bars:
            raise ValueError(
                f"Insufficient aligned historical bars for {fund_id} "
                f"({len(panel)} rows, need {min_aligned_bars}). "
                "Run market backfill with limit >= 756 for 3-year optimization."
            )

        policy = fund.allocation_policy or {}
        rebalance_freq = int(
            cfg.rebalance_freq_days
            if cfg.rebalance_freq_days is not None
            else policy.get("rebalance_freq_days", 7)
        )
        drift_band = cfg.drift_band_pct
        max_position_cap = 100.0
        if fund.mandate:
            max_position_cap = float(fund.mandate.max_position_size_pct or 100.0)

        cash = initial_capital
        holdings: dict[str, float] = {s: 0.0 for s in panel.columns}
        target_weights: dict[str, float] = {}
        equity_curve: list[dict] = []
        rebalance_log: list[dict] = []
        rebalance_returns: list[float] = []

        dates = panel.index.tolist()
        last_rebalance_nav = initial_capital
        last_rebalance_idx = 0
        last_regime: str | None = None

        for i, ts in enumerate(dates):
            prices = panel.iloc[i]
            valid_prices = {s: float(prices[s]) for s in panel.columns if pd.notna(prices[s]) and prices[s] > 0}

            nav = cash + sum(holdings.get(s, 0) * valid_prices.get(s, 0) for s in holdings)

            alloc_preview = _compute_targets(
                fund, panel, i, list(panel.columns), max_position_cap, cfg, last_regime,
            )
            regime_changed = last_regime is not None and alloc_preview.get("regime") != last_regime

            calendar_due = i == 0 or (i - last_rebalance_idx) >= rebalance_freq
            drift_due = self._drift_exceeds_band(nav, holdings, valid_prices, target_weights, drift_band)
            regime_due = cfg.rebalance_mode in ("regime_change", "both") and regime_changed

            should_rebalance = False
            if cfg.rebalance_mode == "regime_change":
                should_rebalance = i == 0 or regime_due
            elif cfg.rebalance_mode == "both":
                should_rebalance = i == 0 or calendar_due or drift_due or regime_due
            else:
                should_rebalance = i == 0 or calendar_due or drift_due

            if should_rebalance:
                alloc = alloc_preview
                target_weights = alloc["weights"]
                prev_nav = nav
                cash, holdings, trade_cost = self._rebalance_to_weights(
                    nav, cash, holdings, valid_prices, target_weights,
                )
                nav = cash + sum(holdings.get(s, 0) * valid_prices.get(s, 0) for s in holdings)
                period_ret = (nav / last_rebalance_nav - 1.0) if last_rebalance_nav > 0 and i > 0 else 0.0
                if i > 0:
                    rebalance_returns.append(period_ret)
                rebalance_log.append({
                    "date": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                    "regime": alloc["regime"],
                    "regime_v2": alloc.get("regime_v2"),
                    "risk_on_off": alloc["risk_on_off"],
                    "weights": target_weights,
                    "cash_pct": alloc["cash_pct"],
                    "nav": round(nav, 2),
                    "trade_cost": round(trade_cost, 2),
                })
                last_rebalance_nav = nav
                last_rebalance_idx = i
                last_regime = alloc.get("regime")

            equity_curve.append({
                "time": int(pd.Timestamp(ts).timestamp()),
                "value": round(nav, 2),
                "weights": dict(target_weights),
            })

        metrics = self._compute_fund_metrics(
            equity_curve, initial_capital, dates, fund, rebalance_returns,
        )
        metrics["symbols_used"] = list(panel.columns)
        metrics["simulation_days"] = len(dates)
        metrics["rebalance_count"] = len(rebalance_log)
        if cfg.experiment_type:
            metrics["experiment_type"] = cfg.experiment_type
        if cfg.experiment_label:
            metrics["experiment_label"] = cfg.experiment_label

        policy_snapshot = dict(policy)
        if cfg.method:
            policy_snapshot["method"] = cfg.method
        if cfg.cash_floor_pct is not None:
            policy_snapshot["cash_floor_pct"] = cfg.cash_floor_pct
        if cfg.rebalance_freq_days is not None:
            policy_snapshot["rebalance_freq_days"] = cfg.rebalance_freq_days

        return FundBacktestResult(
            run_id=f"vfr_{uuid.uuid4().hex[:12]}",
            fund_id=fund.id,
            validation_type=validation_type,
            period_start=pd.Timestamp(dates[0]).to_pydatetime(),
            period_end=pd.Timestamp(dates[-1]).to_pydatetime(),
            initial_capital=initial_capital,
            metrics=metrics,
            equity_curve=equity_curve,
            rebalance_log=rebalance_log,
            allocation_policy_snapshot=policy_snapshot,
            data_coverage=coverage,
            experiment_config=cfg.to_dict(),
        )

    def _drift_exceeds_band(
        self,
        nav: float,
        holdings: dict[str, float],
        prices: dict[str, float],
        targets: dict[str, float],
        band_pct: float = REBALANCE_BAND_PCT,
    ) -> bool:
        if nav <= 0 or not targets:
            return False
        for sym, tgt in targets.items():
            current_val = holdings.get(sym, 0) * prices.get(sym, 0)
            current_pct = (current_val / nav) * 100
            if abs(current_pct - tgt) > band_pct:
                return True
        return False

    def _rebalance_to_weights(
        self,
        nav: float,
        cash: float,
        holdings: dict[str, float],
        prices: dict[str, float],
        targets: dict[str, float],
    ) -> tuple[float, dict[str, float], float]:
        total_cost = 0.0
        new_holdings = dict(holdings)
        for sym in list(new_holdings.keys()):
            if sym not in prices:
                continue
            target_val = nav * (targets.get(sym, 0) / 100.0)
            current_val = new_holdings[sym] * prices[sym]
            delta_val = target_val - current_val
            if abs(delta_val) < 1.0:
                continue
            cost = abs(delta_val) * (COMMISSION_PCT + SLIPPAGE_PCT) / 100.0
            total_cost += cost
            if delta_val > 0 and cash >= delta_val + cost:
                shares = delta_val / prices[sym]
                new_holdings[sym] += shares
                cash -= delta_val + cost
            elif delta_val < 0:
                shares = abs(delta_val) / prices[sym]
                new_holdings[sym] = max(0, new_holdings[sym] - shares)
                cash += abs(delta_val) - cost
        return cash, new_holdings, total_cost

    def _compute_fund_metrics(
        self,
        equity_curve: list[dict],
        initial_capital: float,
        dates: list,
        fund: domain.Fund,
        rebalance_returns: list[float],
    ) -> dict[str, Any]:
        values = [p["value"] for p in equity_curve]
        ts_index = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
        equity = pd.Series(values, index=ts_index)
        returns = pe.daily_returns_from_equity(equity)

        cagr = pe.cagr_pct(equity)
        mdd = pe.max_drawdown_pct(equity)
        ann_vol = pe.volatility_annualized(returns)
        sharpe = pe.sharpe_ratio(returns)
        sortino = pe.sortino_ratio(returns)
        calmar = pe.calmar_ratio(cagr, mdd)

        total_return = (values[-1] / initial_capital - 1.0) * 100 if values else 0.0

        monthly = equity.resample("ME").last().pct_change().dropna()
        avg_monthly = float(monthly.mean() * 100) if len(monthly) else None
        ann_return = cagr

        weekly = equity.resample("W").last().pct_change().dropna()
        avg_weekly = float(weekly.mean() * 100) if len(weekly) else None

        wins = sum(1 for r in rebalance_returns if r > 0)
        win_rate = (wins / len(rebalance_returns) * 100) if rebalance_returns else None

        gains = sum(r for r in rebalance_returns if r > 0)
        losses = abs(sum(r for r in rebalance_returns if r < 0))
        profit_factor = round(gains / losses, 4) if losses > 0 else None

        target_weekly = fund.target_weekly_return_pct
        yield_weeks_met = 0
        yield_weeks_total = 0
        if target_weekly is not None and len(weekly) > 0:
            for wr in weekly:
                if pd.isna(wr):
                    continue
                yield_weeks_total += 1
                if wr * 100 >= target_weekly:
                    yield_weeks_met += 1
        yield_delivery_pct = (
            round(yield_weeks_met / yield_weeks_total * 100, 2) if yield_weeks_total else None
        )

        alpha_target = fund.target_monthly_return_pct
        meets_alpha = avg_monthly is not None and alpha_target is not None and avg_monthly >= alpha_target

        return {
            "total_return_pct": round(total_return, 2),
            "cagr_pct": cagr,
            "annualized_return_pct": ann_return,
            "avg_monthly_return_pct": round(avg_monthly, 2) if avg_monthly is not None else None,
            "avg_weekly_return_pct": round(avg_weekly, 2) if avg_weekly is not None else None,
            "weekly_return_pct": pe.period_return_pct(equity, 7),
            "monthly_return_pct": pe.period_return_pct(equity, 30),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "max_drawdown_pct": mdd,
            "volatility_pct": round(ann_vol * 100, 2) if ann_vol is not None else None,
            "win_rate_pct": round(win_rate, 2) if win_rate is not None else None,
            "profit_factor": profit_factor,
            "final_equity": round(values[-1], 2) if values else initial_capital,
            "yield_delivery_pct": yield_delivery_pct,
            "target_weekly_return_pct": target_weekly,
            "target_monthly_return_pct": alpha_target,
            "meets_target_monthly": meets_alpha if fund.id == "ALPHA" else None,
            "alpha_20pct_supported": meets_alpha if fund.id == "ALPHA" else None,
        }

    def persist_run(
        self,
        result: FundBacktestResult,
        rank_score: float | None = None,
        provenance: str = "VALIDATED_HISTORICAL",
    ) -> domain.ValidatedFundRun:
        exp_cfg = getattr(result, "experiment_config", {}) or {}
        metrics = dict(result.metrics)
        if rank_score is not None:
            metrics["rank_score"] = rank_score
        row = domain.ValidatedFundRun(
            id=result.run_id,
            fund_id=result.fund_id,
            validation_type=result.validation_type,
            period_start=result.period_start,
            period_end=result.period_end,
            initial_capital=result.initial_capital,
            metrics=metrics,
            equity_curve=result.equity_curve,
            rebalance_log=result.rebalance_log,
            allocation_policy_snapshot=result.allocation_policy_snapshot,
            data_coverage=result.data_coverage,
            data_source=result.data_source,
            provenance=provenance,
            experiment_config=exp_cfg,
            rank_score=rank_score,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def run_all_funds(
        self,
        initial_capital: float = 1_000_000.0,
        bar_limit: int = DEFAULT_BAR_LIMIT,
        persist: bool = True,
    ) -> list[FundBacktestResult]:
        funds = self.db.query(domain.Fund).filter(domain.Fund.is_active == True).order_by(domain.Fund.pk_id).all()
        results: list[FundBacktestResult] = []
        for fund in funds:
            try:
                result = self.run_fund_backtest(fund.id, initial_capital, bar_limit)
                if persist:
                    self.persist_run(result)
                results.append(result)
                logger.info(
                    "Fund backtest %s: CAGR=%s%% monthly=%s%% maxDD=%s%%",
                    fund.id,
                    result.metrics.get("cagr_pct"),
                    result.metrics.get("avg_monthly_return_pct"),
                    result.metrics.get("max_drawdown_pct"),
                )
            except Exception as e:
                logger.error("Fund backtest failed for %s: %s", fund.id, e, exc_info=True)
                results.append(FundBacktestResult(
                    run_id=f"vfr_err_{uuid.uuid4().hex[:8]}",
                    fund_id=fund.id,
                    validation_type="BACKTEST",
                    period_start=None,
                    period_end=None,
                    initial_capital=initial_capital,
                    metrics={"error": str(e)},
                ))
        return results

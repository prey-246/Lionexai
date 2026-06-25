import uuid
from datetime import date, datetime
from typing import List, Dict, Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base

# --- Core Models ---

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(30), primary_key=True, default=lambda: f"usr_{uuid.uuid4().hex[:12]}")
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_tier: Mapped[str] = mapped_column(String, default="client") # e.g., 'client', 'admin'
    portfolios: Mapped[List["Portfolio"]] = relationship(back_populates="user")

class Mandate(Base):
    __tablename__ = "mandates"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g., 'PRESERVE'
    name: Mapped[str] = mapped_column(String, nullable=False, default="Mandate")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    risk_tier: Mapped[str] = mapped_column(String, default="Medium")
    max_position_size_pct: Mapped[float] = mapped_column(Float, default=10.0)
    max_portfolio_exposure_pct: Mapped[float] = mapped_column(Float, default=100.0)
    max_leverage: Mapped[float] = mapped_column(Float, default=1.0)
    daily_loss_limit_pct: Mapped[float] = mapped_column(Float)
    max_drawdown_pct: Mapped[float] = mapped_column(Float)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=10)
    restricted_assets_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    kill_switch_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_assets: Mapped[Dict[str, Any]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    kill_switch_active: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    created_by_id: Mapped[str] = mapped_column(String, nullable=True)
    approved_by_id: Mapped[str] = mapped_column(String, nullable=True)
    effective_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    previous_version_pk_id: Mapped[int] = mapped_column(ForeignKey("mandates.pk_id", name="fk_mandate_prev_version", use_alter=True), nullable=True)
    portfolios: Mapped[List["Portfolio"]] = relationship(back_populates="mandate")
    previous_version: Mapped["Mandate"] = relationship("Mandate", remote_side=[pk_id], uselist=False)

class Portfolio(Base):
    __tablename__ = "portfolios"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    mandate_pk_id: Mapped[int] = mapped_column(ForeignKey("mandates.pk_id"), nullable=False)
    total_equity: Mapped[float] = mapped_column(Float, default=0.0)
    available_margin: Mapped[float] = mapped_column(Float, default=0.0)
    current_drawdown_pct: Mapped[float] = mapped_column(Float, default=0.0)
    # Phase 4: link a portfolio to an AI-managed Fund and flag it for autonomous management
    fund_pk_id: Mapped[int | None] = mapped_column(ForeignKey("funds.pk_id", name="fk_portfolios_fund", use_alter=True), nullable=True)
    auto_managed: Mapped[bool] = mapped_column(Boolean, default=False)
    # Phase 4 treasury economics: initial deposit and last weekly settlement timestamp
    principal: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    user: Mapped["User"] = relationship(back_populates="portfolios")
    mandate: Mapped["Mandate"] = relationship(back_populates="portfolios")
    fund: Mapped["Fund"] = relationship("Fund", foreign_keys=[fund_pk_id])
    trades: Mapped[List["Trade"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    risk_events: Mapped[List["RiskEvent"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    equity_curve_points: Mapped[List["EquityCurve"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    allocations: Mapped[List["PortfolioAllocation"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")

    @property
    def mandate_id(self) -> str | None:
        return self.mandate.id if self.mandate else None

    @property
    def risk_context(self) -> Dict[str, Any]:
        if not self.mandate:
            return {}
            
        exposure = 0.0
        try:
            open_trades = [t for t in self.trades if t.status == "OPEN"]
            exposure = sum(t.quantity * t.entry_price for t in open_trades)
        except Exception:
            pass
            
        exposure_pct = (exposure / self.total_equity * 100) if self.total_equity > 0 else 0.0

        return {
            "mandate_name": self.mandate.name,
            "mandate_id": self.mandate.id,
            "risk_tier": self.mandate.risk_tier,
            "daily_loss_limit": self.mandate.daily_loss_limit_pct,
            "daily_loss_limit_pct": self.mandate.daily_loss_limit_pct,
            "max_drawdown": self.mandate.max_drawdown_pct,
            "max_drawdown_pct": self.mandate.max_drawdown_pct,
            "current_drawdown": self.current_drawdown_pct,
            "current_drawdown_pct": self.current_drawdown_pct,
            "capital_at_risk": self.total_equity * (self.mandate.max_drawdown_pct / 100.0),
            "exposure_used": exposure,
            "exposure_utilization_pct": exposure_pct,
            "leverage_used": exposure / self.total_equity if self.total_equity > 0 else 0.0,
            "leverage_limit": self.mandate.max_leverage,
            "kill_switch_status": self.mandate.kill_switch_active
        }

class Trade(Base):
    __tablename__ = "trades"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"trd_{uuid.uuid4().hex[:12]}") # noqa
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.pk_id", name="fk_trades_portfolio_id", use_alter=True), nullable=False) # noqa
    symbol: Mapped[str] = mapped_column(String, index=True)
    # Phase 4: optional link to the multi-asset registry (symbol kept for back-compat)
    asset_pk_id: Mapped[int | None] = mapped_column(ForeignKey("assets.pk_id", name="fk_trades_asset", use_alter=True), nullable=True)
    side: Mapped[str] = mapped_column(String)  # 'BUY' or 'SELL'
    quantity: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="OPEN")  # OPEN, CLOSED, REJECTED
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    execution_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    strategy_name: Mapped[str | None] = mapped_column(String, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    trade_source: Mapped[str] = mapped_column(String, default="MANUAL", index=True)  # AUTONOMOUS, MANUAL, SEED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", foreign_keys=[portfolio_id], back_populates="trades")

    @property
    def size(self) -> float:
        return self.quantity

# --- Monitoring & Analytics Models ---

class RiskEvent(Base):
    __tablename__ = "risk_events"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"re_{uuid.uuid4().hex[:12]}")
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.pk_id", name="fk_risk_events_portfolio_id", use_alter=True), index=True, nullable=False) # noqa
    event_type: Mapped[str] = mapped_column(String, index=True) # e.g., 'MAX_DRAWDOWN_BREACH', 'RISK_REJECTION'
    severity: Mapped[str] = mapped_column(String, default="INFO")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", foreign_keys=[portfolio_id], back_populates="risk_events")

class EquityCurve(Base):
    __tablename__ = "equity_curves"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.pk_id", name="fk_equity_curves_portfolio_id", use_alter=True), index=True) # noqa
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    equity: Mapped[float] = mapped_column(Float)
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", foreign_keys=[portfolio_id], back_populates="equity_curve_points")

class Report(Base):
    __tablename__ = "reports"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, default=lambda: f"rep_{uuid.uuid4().hex[:12]}")
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.pk_id", name="fk_reports_portfolio_id", use_alter=True), nullable=False) # noqa
    report_type: Mapped[str] = mapped_column(String, default="CUSTOM")
    period_start: Mapped[datetime] = mapped_column(DateTime) # noqa
    period_end: Mapped[datetime] = mapped_column(DateTime)
    performance_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", foreign_keys=[portfolio_id], back_populates="reports")

class ValidationSnapshot(Base):
    __tablename__ = "validation_snapshots"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_key: Mapped[str] = mapped_column(String, unique=True, index=True)
    snapshot_type: Mapped[str] = mapped_column(String, index=True)  # GLOBAL, PORTFOLIO, STRATEGY
    period: Mapped[str] = mapped_column(String, index=True)
    scope_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    filled_orders: Mapped[int] = mapped_column(Integer, default=0)
    rejected_orders: Mapped[int] = mapped_column(Integer, default=0)
    best_portfolio: Mapped[str | None] = mapped_column(String, nullable=True)
    worst_portfolio: Mapped[str | None] = mapped_column(String, nullable=True)
    best_strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    worst_strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    exchange_distribution: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)

    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown_pct: Mapped[float] = mapped_column(Float, default=0.0)

    avg_return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    largest_win: Mapped[float] = mapped_column(Float, default=0.0)
    largest_loss: Mapped[float] = mapped_column(Float, default=0.0)

    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    fill_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)

    chart_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class ValidationSnapshotHistory(Base):
    """Append-only daily archive of validation snapshots for time-series analysis."""
    __tablename__ = "validation_snapshot_history"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    archive_date: Mapped[date] = mapped_column(Date, index=True)
    snapshot_key: Mapped[str] = mapped_column(String, index=True)
    snapshot_type: Mapped[str] = mapped_column(String, index=True)
    period: Mapped[str] = mapped_column(String, index=True)
    scope_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    filled_orders: Mapped[int] = mapped_column(Integer, default=0)
    rejected_orders: Mapped[int] = mapped_column(Integer, default=0)
    best_portfolio: Mapped[str | None] = mapped_column(String, nullable=True)
    worst_portfolio: Mapped[str | None] = mapped_column(String, nullable=True)
    best_strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    worst_strategy: Mapped[str | None] = mapped_column(String, nullable=True)
    exchange_distribution: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)

    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown_pct: Mapped[float] = mapped_column(Float, default=0.0)

    avg_return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    largest_win: Mapped[float] = mapped_column(Float, default=0.0)
    largest_loss: Mapped[float] = mapped_column(Float, default=0.0)

    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    fill_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)

    chart_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"aud_{uuid.uuid4().hex[:12]}")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    action_type: Mapped[str] = mapped_column(String, index=True) # e.g., 'TRADE_EXECUTED', 'RISK_REJECTION'
    description: Mapped[str] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    user_id: Mapped[str] = mapped_column(String, nullable=True)

# --- Strategy & Backtesting Models ---

class Strategy(Base):
    __tablename__ = "strategies"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, default=lambda: f"strat_{uuid.uuid4().hex[:12]}")
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

class BacktestResult(Base):
    __tablename__ = "backtest_results"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.pk_id", name="fk_backtest_results_strategy_id", use_alter=True)) # noqa
    symbol: Mapped[str] = mapped_column(String)
    timeframe: Mapped[str] = mapped_column(String)
    performance_summary: Mapped[Dict[str, Any]] = mapped_column(JSON)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class MarketDataOHLCV(Base):
    __tablename__ = "market_data_ohlcv"
    timestamp: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)

# --- NEXA Intelligence Foundation (AI / Alt-Data Layer) ---

class MarketNewsArticle(Base):
    __tablename__ = "market_news_articles"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"news_{uuid.uuid4().hex[:12]}")
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False) # e.g., 'Reuters', 'CoinDesk'
    url: Mapped[str] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    region: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    asset_classes: Mapped[List[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class EconomicEvent(Base):
    __tablename__ = "economic_events"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"eco_{uuid.uuid4().hex[:12]}")
    event_name: Mapped[str] = mapped_column(String, nullable=False) # e.g., 'US CPI (MoM)'
    country: Mapped[str] = mapped_column(String, nullable=False)
    impact: Mapped[str] = mapped_column(String, nullable=False) # e.g., 'HIGH', 'MEDIUM', 'LOW'
    actual_value: Mapped[str] = mapped_column(String, nullable=True)
    forecast_value: Mapped[str] = mapped_column(String, nullable=True)
    previous_value: Mapped[str] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class NLPSentiment(Base):
    __tablename__ = "nlp_sentiments"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"nlp_{uuid.uuid4().hex[:12]}")
    reference_id: Mapped[str] = mapped_column(String, index=True) # Links to news.id or eco.id
    reference_type: Mapped[str] = mapped_column(String) # 'NEWS' or 'ECONOMIC_EVENT'
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False) # -1.0 (Extreme Fear) to 1.0 (Extreme Greed)
    sentiment_label: Mapped[str] = mapped_column(String, nullable=False) # 'BULLISH', 'BEARISH', 'NEUTRAL'
    model_version: Mapped[str] = mapped_column(String, nullable=True) # e.g., 'finbert-v1'
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

class MarketSensitivityScore(Base):
    __tablename__ = "market_sensitivity_scores"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"sens_{uuid.uuid4().hex[:12]}")
    symbol: Mapped[str] = mapped_column(String, index=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False) # Aggregate AI score -1.0 to 1.0
    contributing_factors: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)

# --- Sprint 5: Treasury Foundation ---

class TreasuryPool(Base):
    __tablename__ = "treasury_pools"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String, unique=True, index=True) # e.g., 'RESERVE', 'YIELD', 'GROWTH', 'OPERATIONS', 'INSURANCE'
    name: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    target_allocation_pct: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

class TreasuryTransaction(Base):
    __tablename__ = "treasury_transactions"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"trx_{uuid.uuid4().hex[:12]}")
    pool_pk_id: Mapped[int] = mapped_column(ForeignKey("treasury_pools.pk_id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False) # Positive for deposit, negative for withdrawal
    transaction_type: Mapped[str] = mapped_column(String, nullable=False) # e.g., 'YIELD_COLLECTION', 'INSURANCE_PAYOUT', 'REBALANCING'
    reference_id: Mapped[str] = mapped_column(String, nullable=True) # e.g., portfolio_id or trade_id
    settlement_pk_id: Mapped[int | None] = mapped_column(
        ForeignKey("client_settlements.pk_id", name="fk_treasury_tx_settlement", use_alter=True),
        nullable=True,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)

class GlobalSettings(Base):
    __tablename__ = "global_settings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default="default")
    environment_state: Mapped[str] = mapped_column(String, default="PAPER")
    extreme_bearish_threshold: Mapped[float] = mapped_column(Float, default=-0.5)
    global_max_leverage: Mapped[float] = mapped_column(Float, default=5.0)
    default_commission_pct: Mapped[float] = mapped_column(Float, default=0.1)
    default_slippage_pct: Mapped[float] = mapped_column(Float, default=0.1)
    global_kill_switch_active: Mapped[bool] = mapped_column(Boolean, default=False)
    # Phase 4: feature flag to toggle the autonomous multi-asset manager (vs legacy executor)
    autonomous_v2_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


# --- Phase 4: Autonomous Multi-Asset Fund Manager ---

class Asset(Base):
    """Normalized registry of every tradable/observable instrument across asset classes."""
    __tablename__ = "assets"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, index=True)  # canonical, e.g. BTC/USDT, XAUUSD, SPX
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    asset_class: Mapped[str] = mapped_column(String, index=True)  # CRYPTO/METAL/ENERGY/EQUITY_INDEX/FX
    data_provider: Mapped[str] = mapped_column(String, default="binance")  # binance/yfinance/mock
    data_symbol: Mapped[str] = mapped_column(String, nullable=False)  # provider-native ticker, e.g. GC=F
    execution_venue: Mapped[str] = mapped_column(String, default="SIMULATED")  # binance/bybit/SIMULATED
    quote_currency: Mapped[str] = mapped_column(String, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_tradable: Mapped[bool] = mapped_column(Boolean, default=True)
    # Phase 6: institutional asset classification
    region: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    risk_tier: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    liquidity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class MarketBar(Base):
    """Unified multi-asset OHLCV store keyed by (symbol, timeframe, timestamp)."""
    __tablename__ = "market_bars"
    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    timeframe: Mapped[str] = mapped_column(String, primary_key=True)  # 1d, 4h, 1h
    timestamp: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)


class Fund(Base):
    """An AI-managed investment product: mandate + asset/strategy universe + allocation policy."""
    __tablename__ = "funds"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String, unique=True, index=True)  # PRESERVE/BALANCE/ALPHA
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    mandate_pk_id: Mapped[int | None] = mapped_column(ForeignKey("mandates.pk_id", name="fk_funds_mandate", use_alter=True), nullable=True)
    # allocation_policy: { method, rebalance_freq_days, cash_floor_pct, max_assets }
    allocation_policy: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    target_return_label: Mapped[str | None] = mapped_column(String, nullable=True)
    target_weekly_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_monthly_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_label: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    mandate: Mapped["Mandate"] = relationship("Mandate", foreign_keys=[mandate_pk_id])
    asset_universe: Mapped[List["FundAssetUniverse"]] = relationship(back_populates="fund", cascade="all, delete-orphan")
    strategy_universe: Mapped[List["FundStrategyUniverse"]] = relationship(back_populates="fund", cascade="all, delete-orphan")


class FundAssetUniverse(Base):
    __tablename__ = "fund_asset_universe"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_pk_id: Mapped[int] = mapped_column(ForeignKey("funds.pk_id", name="fk_fau_fund", use_alter=True), nullable=False, index=True)
    asset_pk_id: Mapped[int] = mapped_column(ForeignKey("assets.pk_id", name="fk_fau_asset", use_alter=True), nullable=False)
    min_weight_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_weight_pct: Mapped[float] = mapped_column(Float, default=100.0)
    fund: Mapped["Fund"] = relationship(back_populates="asset_universe")
    asset: Mapped["Asset"] = relationship("Asset")


class FundStrategyUniverse(Base):
    __tablename__ = "fund_strategy_universe"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_pk_id: Mapped[int] = mapped_column(ForeignKey("funds.pk_id", name="fk_fsu_fund", use_alter=True), nullable=False, index=True)
    strategy_pk_id: Mapped[int] = mapped_column(ForeignKey("strategies.pk_id", name="fk_fsu_strategy", use_alter=True), nullable=False)
    enabled_regimes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=list)  # ["BULL","SIDEWAYS",...]
    fund: Mapped["Fund"] = relationship(back_populates="strategy_universe")
    strategy: Mapped["Strategy"] = relationship("Strategy")


class PortfolioAllocation(Base):
    """Source of truth for an auto-managed portfolio's per-asset target/actual weights."""
    __tablename__ = "portfolio_allocations"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.pk_id", name="fk_pa_portfolio", use_alter=True), index=True, nullable=False)
    asset_pk_id: Mapped[int] = mapped_column(ForeignKey("assets.pk_id", name="fk_pa_asset", use_alter=True), nullable=False)
    strategy_pk_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.pk_id", name="fk_pa_strategy", use_alter=True), nullable=True)
    target_weight_pct: Mapped[float] = mapped_column(Float, default=0.0)
    current_weight_pct: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", foreign_keys=[portfolio_id], back_populates="allocations")
    asset: Mapped["Asset"] = relationship("Asset")


class RebalanceEvent(Base):
    """Audit trail of every allocation decision made by the AllocationEngine."""
    __tablename__ = "rebalance_events"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"reb_{uuid.uuid4().hex[:12]}")
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.pk_id", name="fk_reb_portfolio", use_alter=True), index=True, nullable=False)
    trigger: Mapped[str | None] = mapped_column(String, nullable=True)  # SCHEDULED/REGIME_CHANGE/INITIAL/MANUAL
    regime: Mapped[str | None] = mapped_column(String, nullable=True)
    global_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    decisions: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class MarketRegime(Base):
    """Per-asset or GLOBAL regime classification snapshots."""
    __tablename__ = "market_regimes"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String, index=True)  # GLOBAL or a symbol
    regime: Mapped[str] = mapped_column(String)  # BULL/BEAR/SIDEWAYS/CRISIS
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    indicators: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class GlobalMarketState(Base):
    """Latest macro snapshot used by the allocation engine and the client UI."""
    __tablename__ = "global_market_state"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    global_risk_score: Mapped[float] = mapped_column(Float, default=50.0)  # 0 (calm) .. 100 (crisis)
    market_regime: Mapped[str] = mapped_column(String, default="SIDEWAYS")
    risk_on_off: Mapped[str] = mapped_column(String, default="NEUTRAL")  # RISK_ON/RISK_OFF/NEUTRAL
    asset_ranking: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    macro_inputs: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class StrategyScore(Base):
    """Weekly composite scoring of strategies for self-optimizing allocation."""
    __tablename__ = "strategy_scores"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_pk_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.pk_id", name="fk_ss_strategy", use_alter=True), nullable=True)
    strategy_name: Mapped[str] = mapped_column(String, index=True)
    asset_symbol: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    period: Mapped[str] = mapped_column(String, default="30D")
    sharpe: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class ClientSettlement(Base):
    """Weekly profit-routing ledger for auto-managed fund portfolios."""
    __tablename__ = "client_settlements"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"stl_{uuid.uuid4().hex[:12]}")
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.pk_id", name="fk_settlement_portfolio", use_alter=True),
        index=True,
        nullable=False,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime, index=True)
    iso_week_key: Mapped[str] = mapped_column(String(10), index=True)  # e.g. 2026-W25
    opening_equity: Mapped[float] = mapped_column(Float, default=0.0)
    closing_marked_equity: Mapped[float] = mapped_column(Float, default=0.0)
    period_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    target_return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    client_entitlement: Mapped[float] = mapped_column(Float, default=0.0)
    excess_routed: Mapped[float] = mapped_column(Float, default=0.0)
    shortfall_topup: Mapped[float] = mapped_column(Float, default=0.0)
    uncovered: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default="SETTLED")  # SETTLED / PARTIAL / PASSTHROUGH
    breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class LNXIndexSnapshot(Base):
    """LNX as an ecosystem health index (treasury, performance, execution, AUM growth)."""
    __tablename__ = "lnx_index_snapshots"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nav: Mapped[float] = mapped_column(Float, default=0.0)
    treasury_health: Mapped[float] = mapped_column(Float, default=0.0)
    strategy_performance: Mapped[float] = mapped_column(Float, default=0.0)
    execution_quality: Mapped[float] = mapped_column(Float, default=0.0)
    aum_growth: Mapped[float] = mapped_column(Float, default=0.0)
    composite_index: Mapped[float] = mapped_column(Float, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class ValidatedStrategyRun(Base):
    """Historical / walk-forward / Monte Carlo validation — never mixed with demo ledger."""
    __tablename__ = "validated_strategy_runs"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    strategy_key: Mapped[str] = mapped_column(String(40), index=True)
    symbol: Mapped[str] = mapped_column(String(30), index=True)
    validation_type: Mapped[str] = mapped_column(String(30), index=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    regime_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    equity_curve: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    data_source: Mapped[str] = mapped_column(String(40), default="HISTORICAL_MARKET_BARS")
    provenance: Mapped[str] = mapped_column(String(40), default="VALIDATED_HISTORICAL", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class ValidatedFundRun(Base):
    """Fund-level historical backtest on market_bars — never mixed with demo ledger."""
    __tablename__ = "validated_fund_runs"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    fund_id: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    validation_type: Mapped[str] = mapped_column(String(30), default="BACKTEST", index=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    initial_capital: Mapped[float] = mapped_column(Float, default=1_000_000.0)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    equity_curve: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    rebalance_log: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    allocation_policy_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    data_coverage: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    data_source: Mapped[str] = mapped_column(String(40), default="HISTORICAL_MARKET_BARS")
    provenance: Mapped[str] = mapped_column(String(40), default="VALIDATED_HISTORICAL", index=True)
    experiment_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    rank_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class PaperTradingValidationSnapshot(Base):
    """Live paper-trading performance by period — separate from demo operational snapshots."""
    __tablename__ = "paper_trading_validation_snapshots"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    period: Mapped[str] = mapped_column(String(10), index=True)  # 30D, 60D, 90D, 180D, 365D
    scope: Mapped[str] = mapped_column(String(20), default="GLOBAL")  # GLOBAL, fund_id, portfolio_id
    scope_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    provenance: Mapped[str] = mapped_column(String(40), default="PAPER_LIVE")
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class AllocationIntegrityAlert(Base):
    __tablename__ = "allocation_integrity_alerts"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.pk_id", name="fk_alloc_alert_portfolio", use_alter=True),
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    message: Mapped[str] = mapped_column(String(500))
    symbol: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    metadata_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", foreign_keys=[portfolio_id])


class LiveValidationSnapshot(Base):
    """Paper-live validation metrics — separate from demo and historical validation."""
    __tablename__ = "live_validation_snapshots"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    period: Mapped[str] = mapped_column(String(10), index=True)
    scope: Mapped[str] = mapped_column(String(20), default="GLOBAL")
    scope_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    provenance: Mapped[str] = mapped_column(String(40), default="PAPER_LIVE", index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class ExecutionLifecycleEvent(Base):
    """Full execution traceability: signal → settlement → treasury."""
    __tablename__ = "execution_lifecycle_events"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    stage: Mapped[str] = mapped_column(String(40), index=True)
    trade_id: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    portfolio_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    symbol: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    reference_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class LNXAttributionSnapshot(Base):
    __tablename__ = "lnx_attribution_snapshots"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    index_delta: Mapped[float] = mapped_column(Float, default=0.0)
    direction: Mapped[str] = mapped_column(String(10), default="FLAT")
    attribution: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    components: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class TreasuryVerificationRun(Base):
    __tablename__ = "treasury_verification_runs"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    solvency_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="WATCH")
    issues: Mapped[List[str] | None] = mapped_column(JSON, nullable=True)
    pool_balances: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    routing_integrity_pct: Mapped[float] = mapped_column(Float, default=0.0)
    settlement_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    stress_results: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class InstitutionalReport(Base):
    __tablename__ = "institutional_reports"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    report_type: Mapped[str] = mapped_column(String(30), index=True)
    fund_id: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class MacroDataSnapshot(Base):
    """FRED / macro API snapshots for Market Intelligence V2."""
    __tablename__ = "macro_data_snapshots"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(30), default="FRED")
    series_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    risk_drivers: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
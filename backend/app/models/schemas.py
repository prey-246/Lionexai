from pydantic import BaseModel, Field
from uuid import UUID
from typing import List, Any
from datetime import datetime

# --- User Schemas ---
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: str
    is_active: bool
    role_tier: str

    class Config:
        from_attributes = True

# --- Audit Schemas ---
class AuditLog(BaseModel):
    id: str
    timestamp: datetime
    action_type: str
    description: str | None = None
    metadata_json: Any | None = None

    class Config:
        from_attributes = True

class PaginatedAuditLogs(BaseModel):
    logs: List[AuditLog]
    total: int
    limit: int
    offset: int

# --- Token Schema ---
class Token(BaseModel):
    access_token: str
    token_type: str

# --- Risk Context ---
class PortfolioRiskContext(BaseModel):
    mandate_name: str | None = None
    risk_tier: str | None = None
    daily_loss_limit: float | None = None
    max_drawdown: float | None = None
    current_drawdown: float | None = None
    capital_at_risk: float | None = None
    exposure_used: float | None = None
    leverage_used: float | None = None
    kill_switch_status: bool | None = None
    
    mandate_id: str | None = None
    daily_loss_limit_pct: float | None = None
    max_drawdown_pct: float | None = None
    current_drawdown_pct: float | None = None
    leverage_limit: float | None = None
    exposure_utilization_pct: float | None = None

    class Config:
        from_attributes = True

# --- Portfolio Schemas ---
class PortfolioBase(BaseModel):
    id: str
    total_equity: float
    available_margin: float
    current_drawdown_pct: float

class PortfolioCreate(BaseModel):
    id: str
    mandate_pk_id: int
    total_equity: float

class PortfolioResponse(PortfolioBase):
    user_id: str
    mandate_id: str | None = None
    mandate_pk_id: int
    auto_managed: bool = False
    fund_pk_id: int | None = None
    risk_context: PortfolioRiskContext | None = None

    class Config:
        from_attributes = True

# --- Portfolio Analytics Schemas ---
class PortfolioSummary(BaseModel):
    portfolio_count: int
    total_equity: float
    total_pnl: float
    overall_win_rate_pct: float
    best_performing_id: str | None = None
    worst_performing_id: str | None = None

class PortfolioStats(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl: float
    avg_pnl_per_trade: float
    best_trade_pnl: float
    worst_trade_pnl: float

# --- Report Schemas ---
class ReportPerformanceMetrics(BaseModel):
    total_return_pct: float | None = None
    total_pnl: float
    winning_trades: int
    losing_trades: int
    win_rate_pct: float

class Report(BaseModel):
    id: str
    portfolio_id: int
    report_type: str
    period_start: datetime
    period_end: datetime
    performance_metrics: ReportPerformanceMetrics
    created_at: datetime

    class Config:
        from_attributes = True

class EquityDataPoint(BaseModel):
    time: int
    value: float

class ReportGenerate(BaseModel):
    portfolio_id: str
    report_type: str
    start_date: datetime | None = None
    end_date: datetime | None = None

# --- Trade Schemas ---
class TradeExecute(BaseModel):
    symbol: str
    side: str
    size: float
    stop_loss: float | None = None

class Trade(BaseModel):
    id: str
    portfolio_id: int
    symbol: str
    side: str
    size: float
    entry_price: float
    exit_price: float | None = None
    status: str
    pnl: float | None = None
    exchange: str | None = None
    execution_latency_ms: float | None = None
    strategy_name: str | None = None
    rejection_reason: str | None = None
    trade_source: str | None = None
    created_at: datetime
    closed_at: datetime | None = None

    class Config:
        from_attributes = True

# --- Risk Schemas ---
class RiskEvent(BaseModel):
    id: str
    portfolio_id: int
    event_type: str
    severity: str | None = "INFO"
    description: str | None = None
    triggered_at: datetime
    resolved: bool | None = False

    class Config:
        from_attributes = True

class TradeResponse(BaseModel):
    status: str
    trade_id: str
    fill_price: float

# --- Backtest Schemas ---
class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    strategy: str
    initial_capital: float
    commission_pct: float | None = None
    slippage_pct: float | None = None
    strategy_params: dict | None = None

class BacktestMetrics(BaseModel):
    final_capital: float
    total_return_pct: float
    gross_return_pct: float = 0.0
    net_return_pct: float = 0.0
    total_fees_paid: float = 0.0
    slippage_impact: float = 0.0
    max_drawdown_pct: float
    win_rate_pct: float
    sharpe_ratio: float
    total_trades_simulated: int

class BacktestResponse(BaseModel):
    status: str
    symbol: str
    metrics: BacktestMetrics
    equity_curve: List[Any]

    class Config:
        from_attributes = True

# --- NEXA Intelligence Schemas ---
class MarketNewsArticle(BaseModel):
    id: str
    title: str
    source: str
    url: str | None = None
    content: str | None = None
    published_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class EconomicEvent(BaseModel):
    id: str
    event_name: str
    country: str
    impact: str
    actual_value: str | None = None
    forecast_value: str | None = None
    previous_value: str | None = None
    timestamp: datetime

    class Config:
        from_attributes = True

class MarketSensitivityScore(BaseModel):
    id: str
    symbol: str
    score: float
    contributing_factors: dict | None = None
    timestamp: datetime

    class Config:
        from_attributes = True

# --- System Settings Schemas ---
class GlobalSettingsBase(BaseModel):
    environment_state: str
    extreme_bearish_threshold: float
    global_max_leverage: float
    default_commission_pct: float
    default_slippage_pct: float
    global_kill_switch_active: bool

class GlobalSettingsUpdate(BaseModel):
    environment_state: str | None = None
    extreme_bearish_threshold: float | None = None
    global_max_leverage: float | None = None
    default_commission_pct: float | None = None
    default_slippage_pct: float | None = None
    global_kill_switch_active: bool | None = None

class GlobalSettings(GlobalSettingsBase):
    id: str
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Phase 4: Multi-Asset Autonomous Fund Manager Schemas ---

class Asset(BaseModel):
    pk_id: int
    symbol: str
    display_name: str
    asset_class: str
    data_provider: str
    data_symbol: str
    execution_venue: str
    quote_currency: str
    is_active: bool
    is_tradable: bool

    class Config:
        from_attributes = True


class AssetCreate(BaseModel):
    symbol: str
    display_name: str
    asset_class: str
    data_provider: str = "mock"
    data_symbol: str
    execution_venue: str = "SIMULATED"
    quote_currency: str = "USD"
    is_active: bool = True
    is_tradable: bool = True


class AssetUpdate(BaseModel):
    display_name: str | None = None
    asset_class: str | None = None
    data_provider: str | None = None
    data_symbol: str | None = None
    execution_venue: str | None = None
    quote_currency: str | None = None
    is_active: bool | None = None
    is_tradable: bool | None = None


class FundAssetUniverseItem(BaseModel):
    symbol: str
    display_name: str
    asset_class: str
    min_weight_pct: float
    max_weight_pct: float


class FundResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    mandate_id: str | None = None
    risk_label: str | None = None
    target_return_label: str | None = None
    target_weekly_return_pct: float | None = None
    target_monthly_return_pct: float | None = None
    actual_weekly_return_pct: float | None = None
    actual_monthly_return_pct: float | None = None
    actual_total_return_pct: float | None = None
    total_aum: float | None = None
    portfolio_count: int | None = None
    data_provenance: str | None = None  # DEMO | PAPER_LIVE | MIXED | UNKNOWN
    allocation_policy: dict | None = None
    is_active: bool
    asset_universe: List[FundAssetUniverseItem] = []

    class Config:
        from_attributes = True


class FundInvestRequest(BaseModel):
    amount: float = Field(..., gt=0)
    portfolio_id: str | None = None  # optional custom id; auto-generated otherwise


class AllocationItem(BaseModel):
    symbol: str
    display_name: str | None = None
    asset_class: str | None = None
    target_weight_pct: float
    current_weight_pct: float
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class RebalanceEventResponse(BaseModel):
    id: str
    portfolio_id: int
    trigger: str | None = None
    regime: str | None = None
    global_risk_score: float | None = None
    decisions: Any | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class GlobalMarketStateResponse(BaseModel):
    global_risk_score: float
    market_regime: str
    risk_on_off: str
    asset_ranking: Any | None = None
    macro_inputs: Any | None = None
    computed_at: datetime

    class Config:
        from_attributes = True


class MarketRegimeResponse(BaseModel):
    scope: str
    regime: str
    confidence: float
    indicators: Any | None = None
    detected_at: datetime

    class Config:
        from_attributes = True


class ClientSettlementResponse(BaseModel):
    id: str
    portfolio_id: int
    period_start: datetime
    period_end: datetime
    iso_week_key: str
    opening_equity: float
    closing_marked_equity: float
    period_pnl: float
    target_return_pct: float
    client_entitlement: float
    excess_routed: float
    shortfall_topup: float
    uncovered: float
    status: str
    breakdown: Any | None = None
    created_at: datetime
    # Client-facing aliases
    starting_nav: float | None = None
    trading_pnl: float | None = None
    target_yield: float | None = None
    treasury_routed: float | None = None
    shortfall_topups: float | None = None
    lnx_contribution: float | None = None

    class Config:
        from_attributes = True


class LNXIndexResponse(BaseModel):
    nav: float
    treasury_health: float
    strategy_performance: float
    execution_quality: float
    aum_growth: float
    composite_index: float
    computed_at: datetime
    weekly_change_pct: float | None = None
    monthly_change_pct: float | None = None
    treasury_nav: float | None = None
    aum: float | None = None
    reserve_ratio: float | None = None

    class Config:
        from_attributes = True
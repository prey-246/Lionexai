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
    commission_pct: float = 0.1
    slippage_pct: float = 0.1
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
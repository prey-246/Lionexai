from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Any

# ====== User Schemas ======
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ReportGenerate(BaseModel):
    portfolio_id: str
    report_type: str
    start_date: datetime | None = None
    end_date: datetime | None = None

class Report(BaseModel):
    id: str
    portfolio_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    performance_metrics: dict
    risk_metrics: dict
    trades_summary: dict
    created_at: datetime

    class Config:
        from_attributes = True

# ====== Audit Schemas ======
class AuditLog(BaseModel):
    id: str
    timestamp: datetime
    action_type: str
    description: str
    metadata_json: Any | None = None

    class Config:
        from_attributes = True

class PaginatedAuditLogs(BaseModel):
    total: int
    limit: int
    offset: int
    logs: List[AuditLog]

# ====== Auth Schemas ======
class Token(BaseModel):
    access_token: str
    token_type: str

# ====== Mandate Schemas ======
class Mandate(BaseModel):
    id: str
    name: str
    max_leverage: float
    max_drawdown_pct: float
    daily_loss_limit_pct: float
    kill_switch_active: bool

    class Config:
        from_attributes = True

# ====== Portfolio Schemas ======
class PortfolioCreate(BaseModel):
    id: str
    mandate_id: str
    total_equity: float = 100000.0

class PortfolioUpdate(BaseModel):
    mandate_id: str

class Portfolio(BaseModel):
    id: str
    user_id: str
    mandate_id: str
    total_equity: float
    available_margin: float
    current_drawdown_pct: float

    class Config:
        from_attributes = True

class PortfolioSummary(BaseModel):
    portfolio_count: int
    total_equity: float
    total_pnl: float
    overall_win_rate_pct: float
    best_performing_portfolio: str | None
    worst_performing_portfolio: str | None

class PortfolioStats(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl: float
    avg_pnl_per_trade: float
    best_trade_pnl: float
    worst_trade_pnl: float

class TradeExecute(BaseModel):
    symbol: str
    side: str
    size: float
    stop_loss: float | None = None

class TradeResponse(BaseModel):
    status: str
    trade_id: str
    fill_price: float

class Trade(BaseModel):
    id: str
    portfolio_id: str
    symbol: str
    side: str
    size: float
    entry_price: float
    exit_price: float | None = None
    status: str
    pnl: float
    created_at: datetime
    closed_at: datetime | None = None

    class Config:
        from_attributes = True

class RiskEvent(BaseModel):
    id: str
    portfolio_id: str
    event_type: str
    severity: str
    description: str
    triggered_at: datetime
    resolved: bool

    class Config:
        from_attributes = True

# ====== Backtest Schemas ======
class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str
    strategy: str
    initial_capital: float = 100000.0
    strategy_params: dict[str, Any] | None = None

class BacktestMetrics(BaseModel):
    final_capital: float
    total_return_pct: float
    max_drawdown_pct: float
    win_rate_pct: float
    sharpe_ratio: float
    total_trades_simulated: int

class EquityDataPoint(BaseModel):
    time: int
    value: float

class BacktestResponse(BaseModel):
    status: str
    symbol: str
    metrics: BacktestMetrics
    equity_curve: List[EquityDataPoint]
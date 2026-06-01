from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Any

# ====== User Schemas ======
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# ====== Audit Schemas ======
class AuditLog(BaseModel):
    id: int
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
class Portfolio(BaseModel):
    id: str
    user_id: int
    mandate_id: str
    total_equity: float
    available_margin: float
    current_drawdown_pct: float

    class Config:
        from_attributes = True

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
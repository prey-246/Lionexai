from sqlalchemy import Boolean, Column, String, TIMESTAMP, Float, JSON, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: f"user_{uuid.uuid4().hex}")
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_tier = Column(String, default="retail")
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    portfolios = relationship("Portfolio", back_populates="owner")

class Mandate(Base):
    __tablename__ = "mandates"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    max_leverage = Column(Float, nullable=False)
    max_drawdown_pct = Column(Float, nullable=False)
    daily_loss_limit_pct = Column(Float)
    weekly_loss_limit_pct = Column(Float)
    max_position_size_pct = Column(Float)
    max_trade_frequency_per_hour = Column(Integer)
    allowed_assets = Column(JSON, default=["ALL"])
    kill_switch_active = Column(Boolean, default=False)

class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(String, primary_key=True, default=lambda: f"port_{uuid.uuid4().hex}")
    user_id = Column(String, ForeignKey("users.id"))
    mandate_id = Column(String, ForeignKey("mandates.id"))
    total_equity = Column(Float, default=100000.0)
    available_margin = Column(Float, default=100000.0)
    current_drawdown_pct = Column(Float, default=0.0)
    owner = relationship("User", back_populates="portfolios")
    mandate = relationship("Mandate")
    trades = relationship("Trade", back_populates="portfolio")

class Trade(Base):
    __tablename__ = "trades"
    id = Column(String, primary_key=True, default=lambda: f"trade_{uuid.uuid4().hex}")
    portfolio_id = Column(String, ForeignKey("portfolios.id"))
    symbol = Column(String, index=True)
    side = Column(String)
    size = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float)
    status = Column(String, index=True) # OPEN, CLOSED, REJECTED
    pnl = Column(Float, default=0.0)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    closed_at = Column(TIMESTAMP(timezone=True))
    portfolio = relationship("Portfolio", back_populates="trades")

class RiskEvent(Base):
    __tablename__ = "risk_events"
    id = Column(String, primary_key=True, default=lambda: f"re_{uuid.uuid4().hex}")
    portfolio_id = Column(String, ForeignKey("portfolios.id"))
    event_type = Column(String)
    severity = Column(String) # INFO, WARNING, CRITICAL
    description = Column(String)
    triggered_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    metadata_json = Column(JSON)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=lambda: f"audit_{uuid.uuid4().hex}")
    timestamp = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, index=True)
    action_type = Column(String)
    description = Column(String)
    metadata_json = Column(JSON)

class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, default=lambda: f"report_{uuid.uuid4().hex}")
    portfolio_id = Column(String, ForeignKey("portfolios.id"))
    report_type = Column(String) # WEEKLY, MONTHLY
    period_start = Column(TIMESTAMP(timezone=True))
    period_end = Column(TIMESTAMP(timezone=True))
    performance_metrics = Column(JSON)
    risk_metrics = Column(JSON)
    trades_summary = Column(JSON)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
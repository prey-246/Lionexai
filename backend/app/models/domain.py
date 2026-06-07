import uuid
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import (
    Boolean,
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    user: Mapped["User"] = relationship(back_populates="portfolios")
    mandate: Mapped["Mandate"] = relationship(back_populates="portfolios")
    trades: Mapped[List["Trade"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    risk_events: Mapped[List["RiskEvent"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    equity_curve_points: Mapped[List["EquityCurve"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")

    @property
    def mandate_id(self) -> str | None:
        return self.mandate.id if self.mandate else None

    @property
    def risk_context(self) -> Dict[str, Any]:
        if not self.mandate:
            return {}
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
            "exposure_used": 0, # Computed dynamically by the risk engine
            "exposure_utilization_pct": 0,
            "leverage_used": 0, # Computed dynamically by the risk engine
            "kill_switch_status": self.mandate.kill_switch_active
        }

class Trade(Base):
    __tablename__ = "trades"
    pk_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id: Mapped[str] = mapped_column(String(30), unique=True, index=True, default=lambda: f"trd_{uuid.uuid4().hex[:12]}") # noqa
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.pk_id", name="fk_trades_portfolio_id", use_alter=True), nullable=False) # noqa
    symbol: Mapped[str] = mapped_column(String, index=True)
    side: Mapped[str] = mapped_column(String)  # 'BUY' or 'SELL'
    quantity: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="OPEN")  # 'OPEN', 'CLOSED'
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
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
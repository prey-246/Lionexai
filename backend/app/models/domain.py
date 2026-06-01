from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    role_tier = Column(String, default="retail") # retail, ops_admin, quant
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    portfolios = relationship("Portfolio", back_populates="owner")

class Mandate(Base):
    """
    Defines the strict risk parameters. E.g., 'PRESERVE', 'BALANCE', 'ALPHA', 'VAULT'
    """
    __tablename__ = "mandates"
    
    id = Column(String, primary_key=True)  # Using string names as ID for easy lookup (e.g., 'LOW_RISK')
    name = Column(String, nullable=False)
    max_leverage = Column(Float, nullable=False)
    max_drawdown_pct = Column(Float, nullable=False)
    daily_loss_limit_pct = Column(Float, nullable=False)
    allowed_assets = Column(JSON, nullable=False) # List of allowed ticker symbols
    kill_switch_active = Column(Boolean, default=False)
    
    portfolios = relationship("Portfolio", back_populates="mandate")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    mandate_id = Column(String, ForeignKey("mandates.id"))
    
    total_equity = Column(Float, default=100000.0)  # Paper trading starting balance
    available_margin = Column(Float, default=100000.0)
    current_drawdown_pct = Column(Float, default=0.0)
    
    owner = relationship("User", back_populates="portfolios")
    mandate = relationship("Mandate", back_populates="portfolios")

class Trade(Base):
    __tablename__ = "trades"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    portfolio_id = Column(String, ForeignKey("portfolios.id"), index=True)
    symbol = Column(String, index=True)
    side = Column(String)  # BUY, SELL
    size = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    status = Column(String, default="OPEN")  # OPEN, CLOSED, REJECTED
    pnl = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    """
    Immutable ledger of all critical system actions (Risk rejections, parameters changes).
    """
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    action_type = Column(String, index=True) # e.g., RISK_REJECTION, KILL_SWITCH_TRIGGERED
    description = Column(String)
    metadata_json = Column(JSON) # Stores the exact state variables at the time of the event

class EquityCurve(Base):
    __tablename__ = "equity_curves"

    id = Column(String, primary_key=True, default=generate_uuid)
    portfolio_id = Column(String, ForeignKey("portfolios.id"), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    equity = Column(Float)
    drawdown_pct = Column(Float, default=0.0)

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    strategy_type = Column(String)  # moving_average, rsi, atr
    parameters = Column(JSON)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    strategy_id = Column(String, ForeignKey("strategies.id"), index=True)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    initial_capital = Column(Float)
    final_equity = Column(Float)
    total_return_pct = Column(Float)
    cagr = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown_pct = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    results_json = Column(JSON)

class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    portfolio_id = Column(String, ForeignKey("portfolios.id"), index=True)
    event_type = Column(String)  # MARGIN_BREACH, LOSS_LIMIT, DRAWDOWN_LIMIT, etc.
    severity = Column(String)  # INFO, WARNING, CRITICAL
    description = Column(String)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved = Column(Boolean, default=False)
    metadata_json = Column(JSON)

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    portfolio_id = Column(String, ForeignKey("portfolios.id"), index=True)
    report_type = Column(String)  # WEEKLY, MONTHLY
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    performance_metrics = Column(JSON)
    risk_metrics = Column(JSON)
    trades_summary = Column(JSON)
    html_content = Column(String, nullable=True)
    pdf_content = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
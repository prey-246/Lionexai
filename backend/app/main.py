from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.api.routes import auth, system, audit, portfolios, reports, trading, backtest
from app.initial_data import seed_db

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    seed_db(db)
    db.close()

# In a real application, you would want to restrict this to your frontend's domain
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your API routers here
app.include_router(auth.router, prefix="/api/auth")
app.include_router(system.router, prefix="/api")
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"],)
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolios"],)
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"],)
app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtesting"])
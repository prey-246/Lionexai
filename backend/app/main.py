from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import auth, system, audit, portfolios, reports

app = FastAPI(title=settings.PROJECT_NAME)

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
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolios"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
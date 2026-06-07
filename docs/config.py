from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    # Infrastructure
    ENVIRONMENT_STATE: Literal["BACKTEST", "PAPER", "DEMO", "LIVE_DISABLED"] = "PAPER"

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # Add other settings from .env as needed

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
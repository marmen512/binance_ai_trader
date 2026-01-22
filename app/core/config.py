from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./data/db.sqlite3"
    REDIS_URL: str = "redis://localhost:6379/0"
    CCXT_EXCHANGE: str = "binance"
    CCXT_API_KEY: Optional[str] = None
    CCXT_API_SECRET: Optional[str] = None
    COPY_PNL_THRESHOLD: float = 100.0
    DECISION_THRESHOLD: float = 0.6
    ALLOW_LIVE_EXECUTION: bool = False
    ONLINE_MODEL_PATH: str = "checkpoints/models/online_model.pkl"

    class Config:
        env_file = ".env"

settings = Settings()

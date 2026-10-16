import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "PortfolioHub 资产罗盘"
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'portfolio.db'}"
    
    # 交易时段配置 (09:15-11:30, 13:00-15:05)
    QUOTE_REFRESH_INTERVAL_SECONDS: int = 10  # 盘中刷新频率
    OFF_MARKET_REFRESH_INTERVAL_SECONDS: int = 60  # 非交易时段刷新频率
    
    # CORS 跨域允许来源
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

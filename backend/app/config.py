from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "DAIRIP"
    APP_ENV: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "mysql+pymysql://dairip_user:dairip_pass@localhost:3306/dairip_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    FORECAST_HORIZON_DAYS: int = 7
    PERISHABLE_RISK_THRESHOLD: float = 1.5

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
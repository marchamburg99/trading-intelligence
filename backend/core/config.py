from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://trading:trading_secret@postgres:5432/trading"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # API Keys
    alpha_vantage_api_key: str = ""
    twelvedata_api_key: str = ""
    newsapi_key: str = ""
    fred_api_key: str = ""
    anthropic_api_key: str = ""

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "TradingIntelligence/1.0"

    # SEC EDGAR
    sec_edgar_user_agent: str = ""

    # App
    environment: str = "development"
    log_level: str = "INFO"
    claude_max_requests_per_minute: int = 10
    default_portfolio_capital: float = 100000.0

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Application configuration loaded from environment variables via pydantic-settings.

Single Settings instance exported as `settings`. All other modules import from here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration for the Candle application."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database — resolved lazily in db/session.py, not validated here
    candle_db_url: str = ""
    candle_db_url_test: str = ""

    # Exchanges (all optional — public OHLCV requires no keys)
    binance_api_key: str = ""
    binance_api_secret: str = ""
    kraken_api_key: str = ""
    kraken_api_secret: str = ""
    coinbase_api_key: str = ""
    coinbase_api_secret: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""        # market alerts — delivered to traders
    telegram_admin_chat_id: str = ""  # operator alerts — job failures, heartbeats

    # Scheduler
    fetch_interval_minutes: int = 60
    screen_interval_minutes: int = 60
    default_timeframe: str = "4h"
    alert_dedup_hours: int = 4

    # API
    api_key: str = ""

    # App
    env: str = "development"

    @property
    def is_production(self) -> bool:
        """Return True when running in production environment."""
        return self.env == "production"


settings = Settings()

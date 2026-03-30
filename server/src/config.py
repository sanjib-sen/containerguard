from functools import lru_cache

from pydantic import AliasChoices, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    pg_dsn: PostgresDsn | None = Field(
        default=None,
        validation_alias=AliasChoices("PG_DSN", "DATABASE_URL"),
    )
    pg_admin_db: str = "postgres"
    heartbeat_monitor_interval_seconds: int = 5
    heartbeat_unreachable_after_seconds: int = 10
    heartbeat_offline_after_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations

import os
import socket
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_default_hostname = os.environ.get("HOSTNAME", socket.gethostname())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    server_url: str = "http://containerguard-server:8000"
    container_id: str = _default_hostname
    hostname: str = _default_hostname
    image: str = "unknown"
    telemetry_interval_seconds: int = 15
    heartbeat_interval_seconds: int = 5
    http_timeout_seconds: float = 10.0
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

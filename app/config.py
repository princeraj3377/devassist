from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: SecretStr = SecretStr(
        "postgresql+asyncpg://devassist:devassist@localhost:5432/devassist"
    )
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    health_check_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Blog API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="ENVIRONMENT",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: list[str] = Field(default_factory=lambda: ["*"], alias="CORS_ORIGINS")
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"], alias="ALLOWED_HOSTS")
    rate_limit_default: str = Field(default="100/minute", alias="RATE_LIMIT_DEFAULT")
    rate_limit_write: str = Field(default="20/minute", alias="RATE_LIMIT_WRITE")
    database_url: str = Field(
        default="postgresql://postgres:dev@localhost:5432/blog",
        alias="DATABASE_URL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

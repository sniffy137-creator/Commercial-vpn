from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]  # backend/


def _running_pytest() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _select_env_file() -> str | None:
    env = (os.getenv("ENV") or os.getenv("APP_ENV") or "").strip().lower()

    env_test = ROOT / ".env.test"
    env_main = ROOT / ".env"

    if env == "test":
        return str(env_test) if env_test.exists() else None

    if _running_pytest() and env_test.exists():
        return str(env_test)

    return str(env_main) if env_main.exists() else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(
        default="Commercial VPN API",
        validation_alias=AliasChoices("APP_NAME", "app_name"),
    )
    env: str = Field(
        default="dev",
        validation_alias=AliasChoices("ENV", "APP_ENV", "env"),
    )

    database_url: str = Field(
        ...,
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    jwt_secret: str = Field(
        ...,
        validation_alias=AliasChoices("JWT_SECRET", "jwt_secret"),
    )
    jwt_alg: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALG", "jwt_alg"),
    )
    access_token_expire_min: int = Field(
        default=60,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MIN", "access_token_expire_min"),
    )


@lru_cache
def get_settings() -> Settings:
    env_file = _select_env_file()
    return Settings(_env_file=env_file, _env_file_encoding="utf-8")


settings = get_settings()

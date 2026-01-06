from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base  # Base.metadata
from app.db.models import User, Server  # noqa: F401 (регистрация моделей в metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _is_template_url(value: str | None) -> bool:
    """
    Проверяем, что в alembic.ini мог остаться шаблон вида ${DATABASE_URL} (или пусто).
    Такое часто бывает при старте в Docker, если подстановка не сработала.
    """
    if not value:
        return True
    v = value.strip()
    # типовые признаки "шаблона", который нельзя парсить как SQLAlchemy URL
    return v.startswith("${") or "${" in v or v in ("None",)


def _resolve_database_url() -> str:
    """
    Источник правды для Alembic:

    1) Если в окружении есть DATABASE_URL -> используем его (Docker / prod / любые скрипты).
    2) Иначе fallback на settings.database_url (dev/test режимы, где settings сам выберет .env/.env.test).

    Важно: возвращаем именно str.
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url and env_url.strip():
        return env_url.strip()
    return str(settings.database_url)


def _apply_url_to_alembic_config() -> str:
    """
    Железобетонно прописываем url в Alembic config:
    - config.set_main_option("sqlalchemy.url", url) для оффлайн/прочих режимов
    - и дополнительно гарантируем, что engine_from_config получит корректный url
      даже если в ini был ${DATABASE_URL}.
    """
    url = _resolve_database_url()

    # если в ini уже есть sql url, но он шаблонный/битый — перезаписываем
    current = config.get_main_option("sqlalchemy.url")
    if _is_template_url(current) or str(current).strip() != url:
        config.set_main_option("sqlalchemy.url", url)

    return url


def run_migrations_offline() -> None:
    url = _apply_url_to_alembic_config()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    engine_from_config читает sqlalchemy.url из dict section.
    ВАЖНО: setdefault() тут не подходит, потому что если в ini уже лежит "${DATABASE_URL}",
    то setdefault НЕ перезапишет, и Alembic упадёт при парсинге URL.
    """
    url = _apply_url_to_alembic_config()

    section = config.get_section(config.config_ini_section) or {}
    # Принудительно кладём корректный url, даже если там уже было "${DATABASE_URL}"
    section["sqlalchemy.url"] = url

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

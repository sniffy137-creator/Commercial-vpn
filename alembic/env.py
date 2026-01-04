from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base  # Base.metadata
from app.db.models import User, Server  # noqa: F401  (регистрация моделей в metadata)

# Alembic Config object
config = context.config

# Настройка логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata для autogenerate
target_metadata = Base.metadata


def _get_sqlalchemy_url() -> str:
    """
    ВАЖНО:
    - Если тесты или внешние скрипты передали sqlalchemy.url
      через Alembic Config (cfg.set_main_option),
      используем его.
    - Иначе fallback на settings.database_url
      (обычный режим запуска приложения).
    """
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def run_migrations_offline() -> None:
    """
    Offline-режим (alembic revision, alembic upgrade --sql).
    """
    url = _get_sqlalchemy_url()

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
    Online-режим (alembic upgrade).
    engine_from_config ОБЯЗАН читать sqlalchemy.url из Alembic Config,
    чтобы cfg.set_main_option("sqlalchemy.url", ...) из pytest работал.
    """
    section = config.get_section(config.config_ini_section) or {}

    # Страховка: если sqlalchemy.url не положили в config,
    # подставляем его сами
    section.setdefault("sqlalchemy.url", _get_sqlalchemy_url())

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


# Точка входа Alembic
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Корень backend/
ROOT = Path(__file__).resolve().parent

# 1) Для тестов грузим .env.test (если есть), иначе .env
ENV_TEST = ROOT / ".env.test"
ENV_MAIN = ROOT / ".env"

if ENV_TEST.exists():
    load_dotenv(ENV_TEST, override=True)
else:
    load_dotenv(ENV_MAIN, override=False)

# 2) Чтобы "import app" работал стабильно
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402
from app.db.session import get_db  # noqa: E402


def _get_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Create backend/.env.test (preferred) or backend/.env"
        )
    return url


@pytest.fixture(scope="session")
def engine() -> Engine:
    return create_engine(_get_db_url(), future=True, pool_pre_ping=True)


@pytest.fixture(scope="session", autouse=True)
def migrate_db(engine: Engine) -> None:
    # 1) чистим схему
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        conn.commit()

    # 2) накатываем миграции
    alembic_ini = ROOT / "alembic.ini"
    if not alembic_ini.exists():
        raise RuntimeError(f"alembic.ini not found at: {alembic_ini}")

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    command.upgrade(cfg, "head")


@pytest.fixture()
def db_session(engine: Engine) -> Session:
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
    session: Session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

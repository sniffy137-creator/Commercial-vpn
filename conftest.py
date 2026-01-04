from __future__ import annotations

import os
import pathlib
import sys

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Корень backend/
ROOT = pathlib.Path(__file__).resolve().parent


def _assert_no_placeholder_revision() -> None:
    versions_dir = ROOT / "alembic" / "versions"
    if not versions_dir.exists():
        return

    bad: list[str] = []
    for p in versions_dir.glob("*.py"):
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            # если вдруг бинарный/битый файл — просто пропустим
            continue
        if "<PUT_YOUR_REV_ID_HERE>" in txt:
            bad.append(str(p))

    if bad:
        raise RuntimeError(
            "Found '<PUT_YOUR_REV_ID_HERE>' in Alembic migrations:\n" + "\n".join(bad)
        )


_assert_no_placeholder_revision()

# чтобы "import app" работал в тестах, даже если pytest запускается из другого места
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402
from app.db.session import get_db  # noqa: E402


def _get_test_db_url() -> str:
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://vpn:vpn@localhost:5432/vpn_test",
    )


@pytest.fixture(scope="session")
def engine() -> Engine:
    url = _get_test_db_url()
    return create_engine(url, future=True, pool_pre_ping=True)


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
    cfg.set_main_option(
        "sqlalchemy.url",
        engine.url.render_as_string(hide_password=False),
    )
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

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models.plan import Plan
from app.db.models.subscription import Subscription
from app.db.models.user import User


def _register(client, *, email: str, password: str):
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _login(client, *, email: str, password: str, device_id: str = "dev-test"):
    r = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": device_id,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _create_plan(
    db: Session,
    *,
    code: str,
    max_servers: int = 1,
    max_devices: int = 1,
    is_active: bool = True,
    name: str | None = None,
    price_cents: int = 0,
    currency: str = "USD",
) -> Plan:
    plan = Plan(
        code=code,
        name=name or code,
        price_cents=price_cents,
        currency=currency,
        max_servers=max_servers,
        max_devices=max_devices,
        is_active=is_active,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _ensure_active_subscription(
    db: Session,
    *,
    user_id: int,
    plan_id: int,
    expires_at: datetime | None = None,
) -> Subscription:
    """
    Делает подписку пользователя активной на указанный план.
    Если строка subscription уже есть (unique user_id) — обновляет её.
    """
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).one_or_none()

    if expires_at is None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    if sub is None:
        sub = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status="active",
            expires_at=expires_at,
        )
        db.add(sub)
    else:
        sub.plan_id = plan_id
        sub.status = "active"
        sub.expires_at = expires_at

    db.commit()
    db.refresh(sub)
    return sub


def test_can_create_first_server(client, db_session: Session):
    plan = _create_plan(db_session, code="p_test_1", max_servers=1)

    email = "u1@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    user = db_session.query(User).filter(User.email == email).one()
    _ensure_active_subscription(db_session, user_id=user.id, plan_id=plan.id)

    token = _login(client, email=email, password=password, device_id="dev-u1")

    r1 = client.post(
        "/servers",
        json={"host": "1.1.1.1", "port": 51820, "name": "s1"},
        headers={"Authorization": f"Bearer {token}", "X-Device-Id": "dev-u1"},
    )
    assert r1.status_code in (200, 201), r1.text


def test_second_server_blocked_by_limit(client, db_session: Session):
    plan = _create_plan(db_session, code="p_test_2", max_servers=1)

    email = "u2@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    user = db_session.query(User).filter(User.email == email).one()
    _ensure_active_subscription(db_session, user_id=user.id, plan_id=plan.id)

    token = _login(client, email=email, password=password, device_id="dev-u2")

    r1 = client.post(
        "/servers",
        json={"host": "2.2.2.2", "port": 51820, "name": "s1"},
        headers={"Authorization": f"Bearer {token}", "X-Device-Id": "dev-u2"},
    )
    assert r1.status_code in (200, 201), r1.text

    r2 = client.post(
        "/servers",
        json={"host": "2.2.2.3", "port": 51820, "name": "s2"},
        headers={"Authorization": f"Bearer {token}", "X-Device-Id": "dev-u2"},
    )
    assert r2.status_code == 403, r2.text

    body = r2.json()
    assert body.get("code") == "plan_limit_exceeded"
    assert body.get("meta", {}).get("resource") == "servers"
    assert body.get("meta", {}).get("limit") == 1


def test_soft_delete_frees_slot(client, db_session: Session):
    plan = _create_plan(db_session, code="p_test_3", max_servers=1)

    email = "u3@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    user = db_session.query(User).filter(User.email == email).one()
    _ensure_active_subscription(db_session, user_id=user.id, plan_id=plan.id)

    token = _login(client, email=email, password=password, device_id="dev-u3")

    r1 = client.post(
        "/servers",
        json={"host": "3.3.3.3", "port": 51820, "name": "s1"},
        headers={"Authorization": f"Bearer {token}", "X-Device-Id": "dev-u3"},
    )
    assert r1.status_code in (200, 201), r1.text
    server_id = r1.json()["id"]

    r_del = client.delete(
        f"/servers/{server_id}",
        headers={"Authorization": f"Bearer {token}", "X-Device-Id": "dev-u3"},
    )
    assert r_del.status_code == 204, r_del.text

    r2 = client.post(
        "/servers",
        json={"host": "3.3.3.4", "port": 51820, "name": "s2"},
        headers={"Authorization": f"Bearer {token}", "X-Device-Id": "dev-u3"},
    )
    assert r2.status_code in (200, 201), r2.text

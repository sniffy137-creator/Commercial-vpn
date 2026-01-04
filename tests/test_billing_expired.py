from datetime import datetime, timedelta, timezone

from tests.test_server_limits import _create_plan, _register


def test_billing_summary_marks_expired_subscription(client, db_session):
    plan = _create_plan(
        db_session,
        code="p_expired",
        max_servers=5,
        max_devices=5,
    )

    email = "expired@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    from app.db.models.user import User
    from app.db.models.subscription import Subscription

    user = db_session.query(User).filter(User.email == email).one()

    # вручную делаем подписку истёкшей
    sub = user.subscription
    sub.plan_id = plan.id
    sub.status = "active"
    sub.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

    db_session.commit()

    # логин нужен только чтобы получить token
    r_login = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-expired-1",
        },
    )
    assert r_login.status_code == 200, r_login.text
    token = r_login.json()["access_token"]

    # billing summary
    r = client.get(
        "/billing/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["status"] == "expired"
    assert body["plan_code"] == "p_expired"

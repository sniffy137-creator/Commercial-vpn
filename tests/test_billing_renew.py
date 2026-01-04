from datetime import datetime, timedelta, timezone

from tests.test_server_limits import _create_plan, _register


def test_renew_makes_expired_active_and_allows_new_device_login(client, db_session):
    plan = _create_plan(db_session, code="p_renew", max_servers=2, max_devices=1)

    email = "renew@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    from app.db.models.user import User
    user = db_session.query(User).filter(User.email == email).one()

    # истекаем подписку вручную
    sub = user.subscription
    sub.plan_id = plan.id
    sub.status = "active"
    sub.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    # логин с device-1 (может пройти, токен выдаётся)
    r_login = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-1",
        },
    )
    assert r_login.status_code == 200, r_login.text
    token = r_login.json()["access_token"]

    # summary -> expired
    r_sum = client.get(
        "/billing/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_sum.status_code == 200, r_sum.text
    assert r_sum.json()["status"] == "expired"

    # renew
    r_renew = client.post(
        "/billing/renew",
        json={"plan_code": "p_renew", "days": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_renew.status_code == 200, r_renew.text
    assert r_renew.json()["status"] == "active"
    assert r_renew.json()["plan_code"] == "p_renew"

    # теперь логин с новым устройством должен работать (активная подписка есть)
    r_login2 = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-2",
        },
    )
    assert r_login2.status_code == 200, r_login2.text

from datetime import datetime, timedelta, timezone

from tests.test_server_limits import _create_plan, _register


def test_resume_returns_409_when_subscription_expired(client, db_session):
    plan = _create_plan(db_session, code="p_expired_resume", max_servers=1, max_devices=1)

    email = "resume_expired@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    from app.db.models.user import User
    user = db_session.query(User).filter(User.email == email).one()

    # делаем подписку истекшей
    sub = user.subscription
    sub.plan_id = plan.id
    sub.status = "active"
    sub.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    # логин, чтобы получить токен
    r_login = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-exp-resume-1",
        },
    )
    assert r_login.status_code == 200, r_login.text
    token = r_login.json()["access_token"]

    # resume -> 409 subscription_expired
    r = client.post(
        "/billing/resume",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409, r.text
    body = r.json()
    assert body["code"] == "subscription_expired"

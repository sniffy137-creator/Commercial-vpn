from datetime import datetime, timedelta, timezone

from tests.test_server_limits import _create_plan, _ensure_active_subscription, _register


def test_cancel_and_resume_subscription_affects_login(client, db_session):
    plan = _create_plan(db_session, code="p_cr", max_servers=2, max_devices=1)

    email = "cr@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    from app.db.models.user import User
    user = db_session.query(User).filter(User.email == email).one()
    _ensure_active_subscription(db_session, user_id=user.id, plan_id=plan.id)

    # login with device-1 -> get token
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

    # cancel
    r_cancel = client.post(
        "/billing/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_cancel.status_code == 200, r_cancel.text
    assert r_cancel.json()["status"] == "canceled"

    # new device login should be blocked (device-2 is new -> needs active subscription)
    r_login2 = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-2",
        },
    )
    assert r_login2.status_code == 403, r_login2.text
    body = r_login2.json()
    assert body["code"] == "no_active_subscription"

    # resume
    r_resume = client.post(
        "/billing/resume",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_resume.status_code == 200, r_resume.text
    assert r_resume.json()["status"] == "active"

    # now new device login should work
    r_login3 = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-2",
        },
    )
    assert r_login3.status_code == 200, r_login3.text

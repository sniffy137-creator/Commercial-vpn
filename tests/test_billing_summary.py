from tests.test_server_limits import _create_plan, _ensure_active_subscription, _register


def test_billing_summary_shows_limits_and_usage(client, db_session):
    plan = _create_plan(db_session, code="p_bill", max_servers=2, max_devices=3)

    email = "bill@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    from app.db.models.user import User
    user = db_session.query(User).filter(User.email == email).one()
    _ensure_active_subscription(db_session, user_id=user.id, plan_id=plan.id)

    # login with device -> token
    r_login = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-bill-1",
        },
    )
    assert r_login.status_code == 200, r_login.text
    token = r_login.json()["access_token"]

    # create 1 server
    r_srv = client.post(
        "/servers",
        json={"name": "s1", "host": "1.1.1.1", "port": 51820},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_srv.status_code == 201, r_srv.text

    # summary
    r = client.get(
        "/billing/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["plan_code"] == "p_bill"
    assert body["max_servers"] == 2
    assert body["max_devices"] == 3
    assert body["servers_used"] == 1
    assert body["devices_used"] == 1

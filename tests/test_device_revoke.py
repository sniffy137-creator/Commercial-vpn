from tests.test_server_limits import _create_plan, _ensure_active_subscription, _register


def test_revoke_device_frees_slot(client, db_session):
    plan = _create_plan(db_session, code="p_dev_revoke", max_servers=1, max_devices=1)

    email = "dev_revoke@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    from app.db.models.user import User
    user = db_session.query(User).filter(User.email == email).one()
    _ensure_active_subscription(db_session, user_id=user.id, plan_id=plan.id)

    # login with device-1 -> OK
    r1 = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-1",
        },
    )
    assert r1.status_code == 200, r1.text
    token = r1.json()["access_token"]

    # login with device-2 -> blocked (limit=1)
    r2 = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-2",
        },
    )
    assert r2.status_code == 403, r2.text
    body = r2.json()
    assert body["code"] == "plan_limit_exceeded"
    assert body["meta"]["resource"] == "devices"

    # list devices -> get id of device-1
    r_list = client.get(
        "/devices",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_list.status_code == 200, r_list.text
    devices = r_list.json()
    assert len(devices) == 1
    dev1_id = devices[0]["id"]

    # revoke device-1
    r_rev = client.post(
        f"/devices/{dev1_id}/revoke",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_rev.status_code == 204, r_rev.text

    # now device-2 should be allowed
    r3 = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Device-Id": "device-2",
        },
    )
    assert r3.status_code == 200, r3.text

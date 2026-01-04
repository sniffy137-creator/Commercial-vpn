def _login(client, email: str, password: str, device_id: str = "dev-admin"):
    r = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded", "X-Device-Id": device_id},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_admin_can_create_and_toggle_plan(client, db_session):
    from tests.test_server_limits import _register
    from app.db.models.user import User

    email = "admin@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    admin = db_session.query(User).filter(User.email == email).one()
    admin.role = "admin"
    db_session.commit()

    token = _login(client, email, password)

    # create plan
    r_create = client.post(
        "/admin/plans",
        json={
            "code": "pro_test",
            "name": "Pro Test",
            "price_cents": 999,
            "currency": "USD",
            "max_servers": 10,
            "max_devices": 5,
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_create.status_code == 201, r_create.text
    plan = r_create.json()
    plan_id = plan["id"]
    assert plan["code"] == "pro_test"

    # deactivate
    r_deact = client.post(
        f"/admin/plans/{plan_id}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_deact.status_code == 200, r_deact.text
    assert r_deact.json()["is_active"] is False

    # activate
    r_act = client.post(
        f"/admin/plans/{plan_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_act.status_code == 200, r_act.text
    assert r_act.json()["is_active"] is True

    # list
    r_list = client.get(
        "/admin/plans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_list.status_code == 200, r_list.text
    assert any(p["code"] == "pro_test" for p in r_list.json())

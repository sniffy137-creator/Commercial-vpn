def _login(client, email: str, password: str, device_id: str = "dev-admin-billing"):
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


def test_admin_billing_users_returns_list(client, db_session):
    # register admin user
    from tests.test_server_limits import _register, _create_plan
    from app.db.models.user import User

    # на всякий случай создадим активный план, чтобы billing.summary мог показать его
    _create_plan(db_session, code="pro_admin_billing", max_servers=10, max_devices=10, is_active=True)

    email = "admin_billing@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    admin = db_session.query(User).filter(User.email == email).one()
    admin.role = "admin"
    db_session.commit()

    token = _login(client, email, password)

    r = client.get(
        "/admin/billing/users",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Device-Id": "dev-admin-billing",
        },
    )
    assert r.status_code == 200, r.text

    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # проверяем структуру первого элемента
    row = data[0]
    assert "id" in row
    assert "email" in row
    assert "role" in row
    assert "billing" in row

    billing = row["billing"]
    # обязательные поля billing.summary
    for key in (
        "status",
        "plan_code",
        "plan_name",
        "expires_at",
        "max_servers",
        "max_devices",
        "servers_used",
        "devices_used",
    ):
        assert key in billing


def test_admin_billing_users_forbidden_for_regular_user(client, db_session):
    from tests.test_server_limits import _register

    email = "user_billing@example.com"
    password = "StrongPass123!"
    _register(client, email=email, password=password)

    token = _login(client, email, password, device_id="dev-user-billing")

    r = client.get(
        "/admin/billing/users",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Device-Id": "dev-user-billing",
        },
    )
    assert r.status_code == 403, r.text

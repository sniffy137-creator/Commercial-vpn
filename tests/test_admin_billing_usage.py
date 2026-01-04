def _login(client, email: str, password: str, device_id: str):
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


def test_admin_billing_users_shows_usage_counters(client, db_session):
    """
    Проверяем реальный usage:
    - обычный пользователь логинится с X-Device-Id => devices_used должен стать 1
    - создаёт 1 сервер => servers_used должен стать 1
    - админ вызывает /admin/billing/users и видит корректные counters именно у этого пользователя
    """
    from tests.test_server_limits import _register
    from app.db.models.user import User

    # --- 1) создаём admin ---
    admin_email = "admin_usage@example.com"
    admin_password = "StrongPass123!"
    _register(client, email=admin_email, password=admin_password)

    admin = db_session.query(User).filter(User.email == admin_email).one()
    admin.role = "admin"
    db_session.commit()

    admin_token = _login(client, admin_email, admin_password, device_id="dev-admin-usage")

    # --- 2) создаём обычного пользователя ---
    user_email = "user_usage@example.com"
    user_password = "StrongPass123!"
    _register(client, email=user_email, password=user_password)

    user = db_session.query(User).filter(User.email == user_email).one()

    # --- 3) логиним обычного пользователя с device-id => device должен появиться (devices_used = 1) ---
    user_token = _login(client, user_email, user_password, device_id="dev-user-usage-1")

    # --- 4) создаём 1 сервер через API ---
    #
    # ВАЖНО:
    # Поля должны соответствовать твоей схеме ServerCreate.
    # В большинстве реализаций это минимум: host + port (+ name опционально).
    # Если у тебя поле называется иначе — поменяй ключи тут, тест останется тем же.
    #
    r_create = client.post(
        "/servers",
        json={
            "host": "10.10.10.10",
            "port": 51820,
            "name": "srv-1",
        },
        headers={
            "Authorization": f"Bearer {user_token}",
            "X-Device-Id": "dev-user-usage-1",
        },
    )
    assert r_create.status_code in (200, 201), r_create.text

    # --- 5) админ запрашивает таблицу биллинга ---
    r = client.get(
        "/admin/billing/users",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Device-Id": "dev-admin-usage",
        },
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert isinstance(rows, list)

    # --- 6) находим строку нужного пользователя и проверяем usage ---
    row = next((x for x in rows if x.get("id") == user.id), None)
    assert row is not None, f"User id={user.id} not found in /admin/billing/users response"

    billing = row["billing"]
    assert billing["servers_used"] == 1, billing
    assert billing["devices_used"] == 1, billing

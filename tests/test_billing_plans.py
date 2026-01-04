from tests.test_server_limits import _create_plan


def test_billing_plans_returns_only_active_plans(client, db_session):
    _create_plan(db_session, code="p_active_1", max_servers=1, max_devices=1, is_active=True)
    _create_plan(db_session, code="p_active_2", max_servers=2, max_devices=2, is_active=True)
    _create_plan(db_session, code="p_inactive", max_servers=99, max_devices=99, is_active=False)

    r = client.get("/billing/plans")
    assert r.status_code == 200, r.text
    body = r.json()

    codes = {p["code"] for p in body}
    assert "p_active_1" in codes
    assert "p_active_2" in codes
    assert "p_inactive" not in codes

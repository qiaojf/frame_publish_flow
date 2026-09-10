from app.core.enums import UserRole


def test_login_success_and_me(client, make_user):
    user = make_user(username="alice", password="Password123!")
    response = client.post("/api/v1/auth/login", json={"username": "alice", "password": "Password123!"})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["user"]["id"] == str(user.id)
    assert body["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["data"]["username"] == "alice"


def test_login_failure_and_disabled_user(client, make_user):
    make_user(username="disabled", password="Password123!", enabled=False)
    bad = client.post("/api/v1/auth/login", json={"username": "disabled", "password": "wrong"})
    assert bad.status_code == 401
    disabled = client.post("/api/v1/auth/login", json={"username": "disabled", "password": "Password123!"})
    assert disabled.status_code == 401
    assert disabled.json()["error_code"] == "ACCOUNT_DISABLED"


def test_user_cannot_access_admin(client, make_user, auth_headers):
    user = make_user(role=UserRole.USER)
    response = client.get("/api/v1/admin/users", headers=auth_headers(user))
    assert response.status_code == 403
    assert response.json()["error_code"] == "ADMIN_REQUIRED"

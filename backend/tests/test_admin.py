from app.core.enums import UserRole


def test_admin_user_crud(client, make_user, auth_headers):
    admin = make_user(username="admin", role=UserRole.ADMIN)
    headers = auth_headers(admin)
    created = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "username": "new-user",
            "display_name": "New User",
            "email": "new@example.com",
            "password": "Password123!",
            "role": "user",
            "enabled": True,
        },
    )
    assert created.status_code == 201
    user_id = created.json()["data"]["id"]
    updated = client.patch(f"/api/v1/admin/users/{user_id}", headers=headers, json={"role": "admin"})
    assert updated.status_code == 200
    assert updated.json()["data"]["role"] == "admin"
    reset = client.post(
        f"/api/v1/admin/users/{user_id}/reset-password",
        headers=headers,
        json={"password": "Another123!"},
    )
    assert reset.status_code == 200
    deleted = client.delete(f"/api/v1/admin/users/{user_id}", headers=headers)
    assert deleted.status_code == 204


def test_model_and_platform_admin_crud(client, make_user, auth_headers):
    admin = make_user(username="admin", role=UserRole.ADMIN)
    headers = auth_headers(admin)
    model = client.post(
        "/api/v1/admin/video-models",
        headers=headers,
        json={
            "name": "Config Model",
            "code": "config-model",
            "provider": "Test",
            "adapter_type": "mock_video",
            "api_key": "model-secret-value",
            "supports_text_to_video": True,
            "capabilities": {"durations": [2]},
        },
    )
    assert model.status_code == 201
    model_body = model.json()["data"]
    assert model_body["api_key_masked"]
    assert "model-secret-value" not in model.text
    model_id = model_body["id"]
    model_updated = client.patch(
        f"/api/v1/admin/video-models/{model_id}",
        headers=headers,
        json={"name": "Updated Config Model", "enabled": False},
    )
    assert model_updated.status_code == 200
    assert model_updated.json()["data"]["enabled"] is False

    platform = client.post(
        "/api/v1/admin/platforms",
        headers=headers,
        json={
            "name": "Config Platform",
            "code": "config-platform",
            "adapter_type": "mock_publish",
            "capabilities": {"supports_video": True, "fields": []},
        },
    )
    assert platform.status_code == 201
    platform_id = platform.json()["data"]["id"]
    account = client.post(
        "/api/v1/admin/accounts",
        headers=headers,
        json={
            "platform_id": platform_id,
            "name": "Secret Account",
            "account_identifier": "secret-account",
            "client_secret": "client-secret-value",
            "access_token": "access-token-value",
            "extra_config": {"simulate_result": "failed"},
            "enabled": True,
        },
    )
    assert account.status_code == 201
    assert "client-secret-value" not in account.text
    assert "access-token-value" not in account.text
    assert account.json()["data"]["extra_config"] == {"simulate_result": "failed"}
    listed = client.get("/api/v1/admin/accounts", headers=headers)
    assert listed.status_code == 200
    assert "client-secret-value" not in listed.text
    assert "access-token-value" not in listed.text
    account_id = account.json()["data"]["id"]
    account_updated = client.patch(
        f"/api/v1/admin/accounts/{account_id}",
        headers=headers,
        json={"name": "Updated Secret Account"},
    )
    assert account_updated.status_code == 200
    platform_updated = client.patch(
        f"/api/v1/admin/platforms/{platform_id}",
        headers=headers,
        json={"name": "Updated Config Platform", "enabled": False},
    )
    assert platform_updated.status_code == 200
    assert client.delete(f"/api/v1/admin/accounts/{account_id}", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/admin/platforms/{platform_id}", headers=headers).status_code == 204
    assert client.delete(f"/api/v1/admin/video-models/{model_id}", headers=headers).status_code == 204


def test_audit_logs_are_admin_only(client, make_user, auth_headers):
    admin = make_user(username="admin", role=UserRole.ADMIN)
    user = make_user(username="normal")
    denied = client.get("/api/v1/admin/logs", headers=auth_headers(user))
    assert denied.status_code == 403
    allowed = client.get("/api/v1/admin/logs", headers=auth_headers(admin))
    assert allowed.status_code == 200

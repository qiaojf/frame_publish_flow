from app.core.enums import UserRole
from app.core.locale import locale_from_accept_language


def test_me_returns_and_updates_preferred_locale(client, make_user, auth_headers, db):
    user = make_user(username="locale-user", preferred_locale="zh-CN")
    headers = auth_headers(user)

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["data"]["preferred_locale"] == "zh-CN"

    updated = client.patch(
        "/api/v1/users/me/preferences",
        headers=headers,
        json={"preferred_locale": "ja-JP"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["preferred_locale"] == "ja-JP"
    db.refresh(user)
    assert user.preferred_locale == "ja-JP"


def test_preference_rejects_an_unsupported_locale(client, make_user, auth_headers):
    user = make_user(username="invalid-locale")
    response = client.patch(
        "/api/v1/users/me/preferences",
        headers=auth_headers(user),
        json={"preferred_locale": "fr-FR"},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "REQUEST_VALIDATION_ERROR"


def test_accept_language_localizes_unauthenticated_errors(client):
    chinese = client.get("/api/v1/auth/me", headers={"Accept-Language": "zh-TW"})
    assert chinese.status_code == 401
    assert chinese.json()["message"] == "请先登录"

    japanese = client.get("/api/v1/auth/me", headers={"Accept-Language": "ja-JP"})
    assert japanese.status_code == 401
    assert japanese.json()["error_code"] == "NOT_AUTHENTICATED"
    assert japanese.json()["message"] == "ログインしてください"

    english = client.post(
        "/api/v1/auth/login",
        headers={"Accept-Language": "en-US"},
        json={"username": "missing", "password": "wrong"},
    )
    assert english.status_code == 401
    assert english.json()["error_code"] == "INVALID_CREDENTIALS"
    assert english.json()["message"] == "Incorrect username or password"


def test_accept_language_parser_honors_quality_and_supported_fallbacks():
    assert locale_from_accept_language("fr-FR, ja-JP;q=0.8, en-US;q=0.9") == "en-US"
    assert locale_from_accept_language("zh-Hant, en;q=0.5") == "zh-CN"
    assert locale_from_accept_language("fr-FR") is None


def test_authenticated_preference_has_priority_over_accept_language(
    client, make_user, auth_headers
):
    user = make_user(
        username="preference-priority",
        role=UserRole.USER,
        preferred_locale="ja-JP",
    )
    headers = {**auth_headers(user), "Accept-Language": "zh-CN"}
    response = client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 403
    assert response.json()["error_code"] == "ADMIN_REQUIRED"
    assert response.json()["message"] == "この機能は管理者のみ利用できます"

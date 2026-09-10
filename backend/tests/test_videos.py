from app.core.enums import UserRole


def test_video_owner_can_view_download_and_delete(client, make_user, make_video, auth_headers):
    owner = make_user(username="owner")
    video = make_video(owner)
    detail = client.get(f"/api/v1/videos/{video.id}", headers=auth_headers(owner))
    assert detail.status_code == 200
    assert detail.json()["data"]["prompt"] == "测试视频"
    download = client.get(f"/api/v1/videos/{video.id}/download", headers=auth_headers(owner))
    assert download.status_code == 200
    assert download.content == b"test-video-content"
    deleted = client.delete(f"/api/v1/videos/{video.id}", headers=auth_headers(owner))
    assert deleted.status_code == 204
    missing = client.get(f"/api/v1/videos/{video.id}", headers=auth_headers(owner))
    assert missing.status_code == 404


def test_video_non_owner_forbidden_admin_allowed(client, make_user, make_video, auth_headers):
    owner = make_user(username="owner")
    other = make_user(username="other")
    admin = make_user(username="admin", role=UserRole.ADMIN)
    video = make_video(owner)
    forbidden = client.get(f"/api/v1/videos/{video.id}", headers=auth_headers(other))
    assert forbidden.status_code == 403
    allowed = client.get(f"/api/v1/videos/{video.id}", headers=auth_headers(admin))
    assert allowed.status_code == 200

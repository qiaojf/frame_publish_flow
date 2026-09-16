from app.core.enums import UserRole
from app.storage import get_storage


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


def test_missing_video_returns_safe_404(client, make_user, auth_headers):
    import uuid

    user = make_user()
    response = client.get(f"/api/v1/videos/{uuid.uuid4()}", headers=auth_headers(user))
    assert response.status_code == 404
    assert response.json()["error_code"] == "VIDEO_NOT_FOUND"
    assert "traceback" not in response.text.lower()


def test_public_video_endpoint_needs_no_login_and_supports_head_and_range(client, make_video):
    video = make_video()
    path = f"/videos-pub/{video.id}"

    public = client.get(path)
    assert public.status_code == 200
    assert public.content == b"test-video-content"
    assert public.headers["content-type"].startswith("video/mp4")
    assert public.headers["content-disposition"].startswith("inline;")
    assert public.headers["cache-control"] == "public, max-age=300"
    assert public.headers["x-content-type-options"] == "nosniff"

    metadata = client.head(path)
    assert metadata.status_code == 200
    assert metadata.content == b""
    assert metadata.headers["content-length"] == str(len(public.content))

    partial = client.get(path, headers={"Range": "bytes=0-3"})
    assert partial.status_code == 206
    assert partial.content == b"test"
    assert partial.headers["content-range"] == f"bytes 0-3/{len(public.content)}"


def test_public_video_endpoint_hides_deleted_and_missing_files(client, db, make_video):
    video = make_video()
    video.is_deleted = True
    db.commit()

    deleted = client.get(f"/videos-pub/{video.id}")
    assert deleted.status_code == 404
    assert deleted.json()["error_code"] == "VIDEO_NOT_FOUND"

    missing_file = make_video()
    get_storage().resolve(missing_file.storage_key).unlink()
    missing = client.get(f"/videos-pub/{missing_file.id}")
    assert missing.status_code == 404
    assert missing.json()["error_code"] == "VIDEO_FILE_NOT_FOUND"

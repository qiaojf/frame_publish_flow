import uuid

from app.adapters.publishing.base import PublishResult
from app.core.enums import PublishStatus
from app.models import PublishAccount, PublishTask
from app.tasks.publish_tasks import run_publish_task
from app.utils.publish_urls import normalize_web_url, resolve_platform_url, resolve_publish_url


def account(**values) -> PublishAccount:
    defaults = {
        "platform_id": uuid.uuid4(),
        "name": "URL mapping account",
        "account_identifier": None,
        "extra_config": {},
        "enabled": True,
    }
    return PublishAccount(**{**defaults, **values})


def test_publish_result_uses_canonical_urls_and_keeps_legacy_alias():
    canonical = PublishResult(
        status="success",
        publish_url="https://example.com/posts/1",
        platform_url="https://example.com/channel",
    )
    legacy = PublishResult(
        status="success",
        platform_post_url="https://legacy.example.com/posts/1",
    )

    assert canonical.publish_url == "https://example.com/posts/1"
    assert canonical.platform_post_url == canonical.publish_url
    assert canonical.platform_url == "https://example.com/channel"
    assert legacy.publish_url == legacy.platform_post_url
    assert legacy.platform_url is None


def test_instagram_platform_url_uses_saved_username():
    selected = account(account_identifier="@creator.name")

    assert resolve_platform_url("instagram", selected) == (
        "https://www.instagram.com/creator.name/"
    )


def test_instagram_platform_url_rejects_account_type_and_uses_selected_account_name():
    selected = account(name="junfeng05", account_identifier="MEDIA_CREATOR")

    assert resolve_platform_url("instagram", selected) == (
        "https://www.instagram.com/junfeng05/"
    )


def test_content_urls_are_built_from_trimmed_platform_ids():
    assert resolve_publish_url("instagram", " Dd2s93-gYEZ ") == (
        "https://www.instagram.com/p/Dd2s93-gYEZ/"
    )
    assert resolve_publish_url("youtube", " N9LiTQZgda8\u00a0") == (
        "https://www.youtube.com/watch?v=N9LiTQZgda8"
    )


def test_youtube_platform_url_prefers_saved_url_then_handle_then_channel_id():
    selected = account(
        channel_id="UC123",
        extra_config={
            "channel_url": "https://www.youtube.com/@saved-channel",
            "channel_handle": "@fallback-handle",
        },
    )
    assert resolve_platform_url("youtube", selected) == (
        "https://www.youtube.com/@saved-channel"
    )

    selected.extra_config = {"channel_handle": "@fallback-handle"}
    assert resolve_platform_url("youtube", selected) == (
        "https://www.youtube.com/@fallback-handle"
    )

    selected.extra_config = {}
    assert resolve_platform_url("youtube", selected) == (
        "https://www.youtube.com/channel/UC123"
    )


def test_invalid_or_unsafe_explicit_url_is_not_returned():
    selected = account(extra_config={"platform_url": "javascript:alert(1)"})

    assert normalize_web_url("javascript:alert(1)") is None
    assert resolve_platform_url("unknown", selected) is None


def test_publish_history_derives_platform_url_for_legacy_record(
    client,
    db,
    make_user,
    make_video,
    make_platform,
    auth_headers,
):
    user = make_user()
    video = make_video(user)
    platform, selected_account = make_platform()
    platform.code = "youtube"
    platform.name = "YouTube"
    selected_account.channel_id = "UC_HISTORY_CHANNEL"
    task = PublishTask(
        video_id=video.id,
        user_id=user.id,
        platform_id=platform.id,
        account_id=selected_account.id,
        title="Historical YouTube publish",
        tags=[],
        platform_payload={},
        platform_overrides={},
        platform_post_id="history-video-id",
        publish_url="https://www.youtube.com/watch?v=history-video-id",
        platform_url=None,
        idempotency_key="historical-publish-url-mapping",
        status=PublishStatus.SUCCESS,
    )
    db.add(task)
    db.commit()

    response = client.get(
        "/api/v1/publish/tasks",
        params={"video_id": str(video.id)},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    result = response.json()["items"][0]
    assert result["publish_url"] == "https://www.youtube.com/watch?v=history-video-id"
    assert result["platform_url"] == "https://www.youtube.com/channel/UC_HISTORY_CHANNEL"


def test_instagram_history_replaces_stale_account_type_url_and_builds_post_url(
    client,
    db,
    make_user,
    make_video,
    make_platform,
    auth_headers,
):
    user = make_user()
    video = make_video(user)
    platform, selected_account = make_platform()
    platform.code = "instagram"
    platform.name = "Instagram"
    selected_account.name = "junfeng05"
    selected_account.account_identifier = "MEDIA_CREATOR"
    task = PublishTask(
        video_id=video.id,
        user_id=user.id,
        platform_id=platform.id,
        account_id=selected_account.id,
        title="Historical Instagram publish",
        tags=[],
        platform_payload={},
        platform_overrides={},
        platform_post_id="Dd2s93-gYEZ",
        publish_url=None,
        platform_url="https://www.instagram.com/MEDIA_CREATOR/",
        idempotency_key="historical-instagram-url-mapping",
        status=PublishStatus.SUCCESS,
    )
    db.add(task)
    db.commit()

    response = client.get(
        "/api/v1/publish/tasks",
        params={"video_id": str(video.id)},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    result = response.json()["items"][0]
    assert result["publish_url"] == "https://www.instagram.com/p/Dd2s93-gYEZ/"
    assert result["platform_url"] == "https://www.instagram.com/junfeng05/"


def test_worker_reuses_existing_permalink_metadata(
    db,
    make_user,
    make_video,
    make_platform,
    monkeypatch,
):
    user = make_user()
    video = make_video(user)
    platform, selected_account = make_platform()
    platform.code = "instagram"
    selected_account.account_identifier = "legacy.creator"
    task = PublishTask(
        video_id=video.id,
        user_id=user.id,
        platform_id=platform.id,
        account_id=selected_account.id,
        title="Metadata compatibility",
        tags=[],
        platform_payload={},
        platform_overrides={},
        idempotency_key="metadata-url-compatibility",
        status=PublishStatus.PENDING,
    )
    db.add(task)
    db.commit()

    class MetadataOnlyAdapter:
        async def publish_video(self, request):
            return PublishResult(
                status="success",
                platform_post_id="legacy-media-id",
                metadata={"permalink": "https://www.instagram.com/reel/LEGACY123/"},
            )

    monkeypatch.setattr(
        "app.tasks.publish_tasks.PublishAdapterFactory.create",
        lambda selected_platform, account: MetadataOnlyAdapter(),
    )
    run_publish_task.run(str(task.id))
    db.expire_all()
    saved = db.get(PublishTask, task.id)

    assert saved.publish_url == "https://www.instagram.com/reel/LEGACY123/"
    assert saved.platform_url == "https://www.instagram.com/legacy.creator/"

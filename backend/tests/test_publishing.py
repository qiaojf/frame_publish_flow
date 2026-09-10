import json
import uuid

import pytest

from app.core.enums import PublishStatus
from app.models import PublishTask
from app.tasks.publish_tasks import run_publish_task


@pytest.fixture
def no_publish_queue(monkeypatch):
    monkeypatch.setattr("app.tasks.publish_tasks.run_publish_task.delay", lambda task_id: None)


def publish_payload(video_id, targets):
    return {
        "video_id": str(video_id),
        "title": "公共标题",
        "description": "公共描述",
        "tags": ["AI", "video"],
        "targets": [
            {"platform_id": str(platform.id), "account_id": str(account.id), "overrides": {}}
            for platform, account in targets
        ],
    }


def test_multi_target_creates_independent_tasks_and_is_idempotent(
    client,
    db,
    make_user,
    make_video,
    make_platform,
    auth_headers,
    no_publish_queue,
):
    user = make_user()
    video = make_video(user)
    targets = [make_platform(), make_platform()]
    payload = publish_payload(video.id, targets)
    headers = {**auth_headers(user), "Idempotency-Key": "same-browser-request"}
    first = client.post("/api/v1/publish/tasks", headers=headers, data={"payload": json.dumps(payload)})
    assert first.status_code == 202
    first_ids = {task["id"] for task in first.json()["data"]["tasks"]}
    assert len(first_ids) == 2
    second = client.post("/api/v1/publish/tasks", headers=headers, data={"payload": json.dumps(payload)})
    second_ids = {task["id"] for task in second.json()["data"]["tasks"]}
    assert first_ids == second_ids
    assert db.query(PublishTask).count() == 2

    changed = {**payload, "title": "不同标题"}
    conflict = client.post(
        "/api/v1/publish/tasks",
        headers=headers,
        data={"payload": json.dumps(changed)},
    )
    assert conflict.status_code == 409


def test_idempotency_key_is_scoped_to_user(
    client,
    db,
    make_user,
    make_video,
    make_platform,
    auth_headers,
    no_publish_queue,
):
    first_user = make_user(username="first-user")
    second_user = make_user(username="second-user")
    first_video = make_video(first_user)
    second_video = make_video(second_user)
    target = make_platform()
    key = "shared-client-key"
    first = client.post(
        "/api/v1/publish/tasks",
        headers={**auth_headers(first_user), "Idempotency-Key": key},
        data={"payload": json.dumps(publish_payload(first_video.id, [target]))},
    )
    second = client.post(
        "/api/v1/publish/tasks",
        headers={**auth_headers(second_user), "Idempotency-Key": key},
        data={"payload": json.dumps(publish_payload(second_video.id, [target]))},
    )
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"]["tasks"][0]["id"] != second.json()["data"]["tasks"][0]["id"]
    assert db.query(PublishTask).count() == 2


def test_publish_other_users_video_is_forbidden(
    client,
    make_user,
    make_video,
    make_platform,
    auth_headers,
    no_publish_queue,
):
    owner = make_user(username="owner")
    other = make_user(username="other")
    video = make_video(owner)
    target = make_platform()
    response = client.post(
        "/api/v1/publish/tasks",
        headers=auth_headers(other),
        data={"payload": json.dumps(publish_payload(video.id, [target]))},
    )
    assert response.status_code == 403


def test_retry_only_failed_task(
    client,
    db,
    make_user,
    make_video,
    make_platform,
    auth_headers,
    no_publish_queue,
):
    user = make_user()
    video = make_video(user)
    target = make_platform()
    created = client.post(
        "/api/v1/publish/tasks",
        headers=auth_headers(user),
        data={"payload": json.dumps(publish_payload(video.id, [target]))},
    )
    task_id = uuid.UUID(created.json()["data"]["tasks"][0]["id"])
    task = db.get(PublishTask, task_id)
    task.status = PublishStatus.FAILED
    db.commit()
    retried = client.post(f"/api/v1/publish/tasks/{task_id}/retry", headers=auth_headers(user))
    assert retried.status_code == 202
    assert retried.json()["data"]["retry_count"] == 1
    db.expire_all()
    task = db.get(PublishTask, task_id)
    task.status = PublishStatus.SUCCESS
    db.commit()
    rejected = client.post(f"/api/v1/publish/tasks/{task_id}/retry", headers=auth_headers(user))
    assert rejected.status_code == 409


def test_mock_publish_tasks_finish_independently(
    db,
    make_user,
    make_video,
    make_platform,
):
    user = make_user()
    video = make_video(user)
    success_platform, success_account = make_platform("success")
    fail_platform, fail_account = make_platform("failed")
    success_task = PublishTask(
        video_id=video.id,
        user_id=user.id,
        platform_id=success_platform.id,
        account_id=success_account.id,
        title="成功",
        tags=[],
        platform_overrides={},
        idempotency_key="success-key",
        status=PublishStatus.PENDING,
    )
    fail_task = PublishTask(
        video_id=video.id,
        user_id=user.id,
        platform_id=fail_platform.id,
        account_id=fail_account.id,
        title="失败",
        tags=[],
        platform_overrides={},
        idempotency_key="fail-key",
        status=PublishStatus.PENDING,
    )
    db.add_all([success_task, fail_task])
    db.commit()
    run_publish_task.run(str(success_task.id))
    run_publish_task.run(str(fail_task.id))
    db.expire_all()
    assert db.get(PublishTask, success_task.id).status == PublishStatus.SUCCESS
    assert db.get(PublishTask, fail_task.id).status == PublishStatus.FAILED


def test_successful_publish_task_is_not_sent_again(
    db,
    make_user,
    make_video,
    make_platform,
    monkeypatch,
):
    user = make_user()
    video = make_video(user)
    platform, account = make_platform("success")
    task = PublishTask(
        video_id=video.id,
        user_id=user.id,
        platform_id=platform.id,
        account_id=account.id,
        title="已发布",
        tags=[],
        platform_overrides={},
        idempotency_key="already-successful-key",
        status=PublishStatus.SUCCESS,
    )
    db.add(task)
    db.commit()

    monkeypatch.setattr(
        "app.tasks.publish_tasks.PublishAdapterFactory.create",
        lambda *args: pytest.fail("已成功任务不应再次调用发布 Adapter"),
    )
    run_publish_task.run(str(task.id))
    db.expire_all()
    assert db.get(PublishTask, task.id).status == PublishStatus.SUCCESS

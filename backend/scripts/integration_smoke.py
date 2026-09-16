"""Run a real full-stack smoke test against a running FrameFlow deployment."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import uuid
from collections.abc import Iterable
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx
from redis import Redis
from sqlalchemy import inspect, select, text

from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.models import PublishAccount, PublishPlatform, User, VideoModel
from app.tasks.celery_app import celery_app


EXPECTED_TABLES = {
    "users",
    "video_models",
    "video_generation_tasks",
    "videos",
    "publish_platforms",
    "publish_accounts",
    "publish_tasks",
    "audit_logs",
}
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
# Larger than Nginx's 1 MB default, but below the application's 10 MB limit.
GATEWAY_UPLOAD_PNG = ONE_PIXEL_PNG + (b"\0" * (2 * 1024 * 1024))


def report(message: str) -> None:
    print(f"[smoke] {message}", flush=True)


def require_response(response: httpx.Response, expected: int | Iterable[int]) -> httpx.Response:
    accepted = {expected} if isinstance(expected, int) else set(expected)
    if response.status_code not in accepted:
        raise AssertionError(
            f"{response.request.method} {response.request.url} returned "
            f"{response.status_code}: {response.text[:1000]}"
        )
    return response


def login(client: httpx.Client, username: str, password: str) -> dict[str, str]:
    response = require_response(
        client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        ),
        200,
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def wait_for_task(
    client: httpx.Client,
    path: str,
    headers: dict[str, str],
    *,
    terminal: set[str],
    timeout_seconds: int,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_status = "unknown"
    while time.monotonic() < deadline:
        response = require_response(client.get(path, headers=headers), 200)
        data = response.json()["data"]
        last_status = data["status"]
        if last_status in terminal:
            return data
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for {path}; last status={last_status}")


def verify_infrastructure() -> None:
    settings = get_settings()
    if engine.dialect.name != "postgresql":
        raise AssertionError(f"Full-stack smoke test requires PostgreSQL, got {engine.dialect.name}")
    with engine.connect() as connection:
        version = str(connection.execute(text("select version()")).scalar_one())
    if "PostgreSQL 17" not in version:
        raise AssertionError(f"Expected PostgreSQL 17, got: {version}")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - tables
    if missing:
        raise AssertionError(f"Missing database tables: {sorted(missing)}")
    if not inspector.get_foreign_keys("publish_tasks"):
        raise AssertionError("publish_tasks foreign keys are missing")
    if not inspector.get_indexes("publish_tasks"):
        raise AssertionError("publish_tasks indexes are missing")
    column_types = {column["name"]: type(column["type"]).__name__ for column in inspector.get_columns("video_models")}
    if column_types.get("capabilities") != "JSONB":
        raise AssertionError(f"video_models.capabilities is not JSONB: {column_types.get('capabilities')}")

    redis_client = Redis.from_url(settings.redis_url, socket_timeout=5)
    if not redis_client.ping():
        raise AssertionError("Redis ping failed")

    worker_deadline = time.monotonic() + 60
    ping: dict = {}
    while time.monotonic() < worker_deadline and not ping:
        ping = celery_app.control.inspect(timeout=5).ping() or {}
        if not ping:
            time.sleep(2)
    if not ping:
        raise AssertionError("No Celery worker responded to ping")
    worker_inspector = celery_app.control.inspect(timeout=8)
    registered = worker_inspector.registered() or {}
    registered_tasks = {task for tasks in registered.values() for task in tasks}
    required_tasks = {"generation.run", "publish.run"}
    if not required_tasks <= registered_tasks:
        raise AssertionError(f"Celery tasks not registered: {sorted(required_tasks - registered_tasks)}")

    for binary in (settings.ffmpeg_binary, settings.ffprobe_binary):
        completed = subprocess.run(
            [binary, "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if completed.returncode != 0:
            raise AssertionError(f"{binary} is not usable: {completed.stderr[-500:]}")
    report("PostgreSQL 17, JSONB/FK/index, Redis, Celery and FFmpeg checks passed")


def verify_seed(admin_username: str) -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == admin_username))
        model = db.scalar(select(VideoModel).where(VideoModel.code == "mock-video"))
        platform = db.scalar(select(PublishPlatform).where(PublishPlatform.code == "mock-platform"))
        account = (
            db.scalar(select(PublishAccount).where(PublishAccount.platform_id == platform.id))
            if platform
            else None
        )
        if not admin or not admin.enabled or admin.role.value != "admin":
            raise AssertionError("Seed admin is missing or disabled")
        if not model or not model.enabled:
            raise AssertionError("Seed Mock Video Model is missing or disabled")
        if not model.supports_text_to_video or not model.supports_image_to_video:
            raise AssertionError("Seed Mock Video Model capabilities are incomplete")
        if not platform or not platform.enabled or not account or not account.enabled:
            raise AssertionError("Seed Mock Platform or Mock Account is missing or disabled")
    report("Seed records are present and enabled")


def run_business_workflow(
    base_url: str,
    admin_username: str,
    admin_password: str,
    default_user_username: str,
    default_user_password: str,
    timeout_seconds: int,
) -> None:
    suffix = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    smoke_username = f"smoke-{suffix}"
    smoke_password = "SmokeUser123!"
    model_secret = f"model-secret-{suffix}"
    account_secret = f"account-secret-{suffix}"

    with httpx.Client(base_url=base_url.rstrip("/"), timeout=30, follow_redirects=True) as client:
        require_response(client.get("/health"), 200)
        require_response(client.get("/openapi.json"), 200)
        require_response(client.get("/docs"), 200)

        admin_headers = login(client, admin_username, admin_password)
        default_user_headers = login(client, default_user_username, default_user_password)
        admin_me = require_response(client.get("/api/v1/auth/me", headers=admin_headers), 200).json()["data"]
        if admin_me["role"] != "admin":
            raise AssertionError("Default admin did not receive the admin role")

        created_user = require_response(
            client.post(
                "/api/v1/admin/users",
                headers=admin_headers,
                json={
                    "username": smoke_username,
                    "display_name": "Full-stack Smoke User",
                    "password": smoke_password,
                    "role": "user",
                    "enabled": True,
                },
            ),
            201,
        )
        smoke_user_id = created_user.json()["data"]["id"]
        user_headers = login(client, smoke_username, smoke_password)
        denied = require_response(client.get("/api/v1/admin/users", headers=user_headers), 403)
        if denied.json().get("error_code") != "ADMIN_REQUIRED":
            raise AssertionError("Non-admin request did not return ADMIN_REQUIRED")
        report("Admin/user authentication and backend RBAC passed")

        seed_models = require_response(client.get("/api/v1/video-models", headers=user_headers), 200).json()["data"]
        if not any(item["code"] == "mock-video" for item in seed_models):
            raise AssertionError("Seed Mock Video Model is not exposed to users")
        admin_models = require_response(
            client.get("/api/v1/admin/video-models", headers=admin_headers, params={"page_size": 100}),
            200,
        ).json()["items"]
        expected_adapters = {
            "google_veo31", "runway_gen45", "runway_seedance25",
            "luma_ray32", "minimax_hailuo23",
        }
        seeded_templates = {item["adapter_type"] for item in admin_models if not item["enabled"]}
        if not expected_adapters.issubset(seeded_templates):
            raise AssertionError("Real model templates were not seeded as disabled entries")

        provider_response = require_response(
            client.post(
                "/api/v1/admin/model-providers",
                headers=admin_headers,
                json={
                    "name": f"Smoke Model Provider {suffix}",
                    "code": f"smoke-model-provider-{suffix}",
                    "adapter_family": "mock",
                    "auth_type": "api_key",
                    "provider_capabilities": {},
                    "enabled": True,
                },
            ),
            201,
        )
        model_account_response = require_response(
            client.post(
                "/api/v1/admin/model-accounts",
                headers=admin_headers,
                json={
                    "provider_id": provider_response.json()["data"]["id"],
                    "name": f"Smoke Model Account {suffix}",
                    "account_identifier": f"smoke-model-account-{suffix}",
                    "api_key": model_secret,
                    "credential_extra": {"private_key": "must-not-be-returned"},
                    "enabled": True,
                },
            ),
            201,
        )
        if model_secret in model_account_response.text or "must-not-be-returned" in model_account_response.text:
            raise AssertionError("Model account API leaked credential material")
        model_account_id = model_account_response.json()["data"]["id"]

        model_response = require_response(
            client.post(
                "/api/v1/admin/video-models",
                headers=admin_headers,
                json={
                    "name": f"Smoke Mock Model {suffix}",
                    "code": f"smoke-mock-model-{suffix}",
                    "model_account_id": model_account_id,
                    "adapter_type": "mock_video",
                    "model_id": "smoke-mock",
                    "supports_text_to_video": True,
                    "supports_image_to_video": True,
                    "capabilities": {
                        "durations": [2],
                        "aspect_ratios": ["16:9"],
                        "resolutions": ["720p"],
                        "max_images": 1,
                    },
                    "extra_config": {"mock_duration_seconds": 2},
                    "enabled": True,
                },
            ),
            201,
        )
        if model_secret in model_response.text or not model_response.json()["data"]["api_key_masked"]:
            raise AssertionError("Video model API leaked or failed to mask its API key")
        model_id = model_response.json()["data"]["id"]
        account_test = require_response(
            client.post(
                f"/api/v1/admin/model-accounts/{model_account_id}/test",
                headers=admin_headers,
            ),
            200,
        ).json()["data"]
        if not account_test["configured"]:
            raise AssertionError(f"Model account validation failed: {account_test}")
        model_test = require_response(
            client.post(f"/api/v1/admin/video-models/{model_id}/test", headers=admin_headers),
            200,
        ).json()["data"]
        if not model_test["configured"]:
            raise AssertionError(f"Model adapter validation failed: {model_test}")

        invalid = require_response(
            client.post(
                "/api/v1/generation/tasks",
                headers=user_headers,
                files={
                    "prompt": (None, "invalid duration"),
                    "model_id": (None, model_id),
                    "duration": (None, "999"),
                },
            ),
            400,
        )
        if invalid.json().get("error_code") != "INVALID_DURATIONS":
            raise AssertionError(f"Unexpected capability error: {invalid.text}")

        text_creation = require_response(
            client.post(
                "/api/v1/generation/tasks",
                headers=user_headers,
                files={
                    "prompt": (None, "A cinematic Tokyo street after rain"),
                    "model_id": (None, model_id),
                    "duration": (None, "2"),
                    "aspect_ratio": (None, "16:9"),
                    "resolution": (None, "720p"),
                },
            ),
            202,
        ).json()["data"]
        text_task = wait_for_task(
            client,
            f"/api/v1/generation/tasks/{text_creation['id']}",
            user_headers,
            terminal={"success", "failed", "timeout", "cancelled"},
            timeout_seconds=timeout_seconds,
        )
        if text_task["status"] != "success" or text_task["generation_type"] != "text_to_video":
            raise AssertionError(f"Text-to-video failed: {text_task}")

        image_creation = require_response(
            client.post(
                "/api/v1/generation/tasks",
                headers=user_headers,
                files={
                    "prompt": (None, "Animate the reference image slowly"),
                    "model_id": (None, model_id),
                    "duration": (None, "2"),
                    "aspect_ratio": (None, "16:9"),
                    "resolution": (None, "720p"),
                    "image": ("reference.png", GATEWAY_UPLOAD_PNG, "image/png"),
                },
            ),
            202,
        ).json()["data"]
        image_task = wait_for_task(
            client,
            f"/api/v1/generation/tasks/{image_creation['id']}",
            user_headers,
            terminal={"success", "failed", "timeout", "cancelled"},
            timeout_seconds=timeout_seconds,
        )
        if image_task["status"] != "success" or image_task["generation_type"] != "image_to_video":
            raise AssertionError(f"Image-to-video failed: {image_task}")
        report("Text-to-video and image-to-video completed through the Celery worker")

        video_id = text_task["video_id"]
        video = require_response(client.get(f"/api/v1/videos/{video_id}", headers=user_headers), 200).json()["data"]
        media = require_response(client.get(video["video_url"]), 200)
        if len(media.content) < 100 or "video" not in media.headers.get("content-type", ""):
            raise AssertionError("Generated video is not playable media")
        download = require_response(client.get(f"/api/v1/videos/{video_id}/download", headers=user_headers), 200)
        if download.content != media.content:
            raise AssertionError("Video download differs from the stored media")
        public_media = require_response(client.get(f"/videos-pub/{video_id}"), 200)
        if public_media.content != media.content:
            raise AssertionError("Public review endpoint differs from the stored media")
        if not public_media.headers.get("content-type", "").startswith("video/"):
            raise AssertionError("Public review endpoint did not return a video content type")
        public_head = require_response(client.head(f"/videos-pub/{video_id}"), 200)
        if int(public_head.headers.get("content-length", 0)) != len(media.content):
            raise AssertionError("Public review endpoint HEAD metadata is incorrect")
        foreign_access = require_response(
            client.get(f"/api/v1/videos/{video_id}", headers=default_user_headers),
            403,
        )
        if foreign_access.json().get("error_code") != "FORBIDDEN":
            raise AssertionError("Foreign video access did not return FORBIDDEN")
        report("Storage, public review media, download and owner permission checks passed")

        targets: list[dict[str, object]] = []
        accounts: list[str] = []
        for index, mode in enumerate(("success", "success", "failed"), start=1):
            platform = require_response(
                client.post(
                    "/api/v1/admin/platforms",
                    headers=admin_headers,
                    json={
                        "name": f"Smoke Platform {index} {suffix}",
                        "code": f"smoke-platform-{index}-{suffix}",
                        "adapter_type": "mock_publish",
                        "capabilities": {
                            "supports_video": True,
                            "supports_cover": True,
                            "requires_account": True,
                            "fields": [],
                        },
                        "enabled": True,
                    },
                ),
                201,
            ).json()["data"]
            account_payload = {
                "platform_id": platform["id"],
                "name": f"Smoke Account {index}",
                "account_identifier": f"smoke-account-{index}-{suffix}",
                "extra_config": {"simulate_result": mode},
                "enabled": True,
            }
            if index == 1:
                account_payload["client_secret"] = account_secret
            account_response = require_response(
                client.post("/api/v1/admin/accounts", headers=admin_headers, json=account_payload),
                201,
            )
            if account_secret in account_response.text:
                raise AssertionError("Publish account API leaked its client secret")
            account = account_response.json()["data"]
            accounts.append(account["id"])
            targets.append(
                {
                    "platform_id": platform["id"],
                    "account_id": account["id"],
                    "overrides": {},
                }
            )

        public_platforms = require_response(
            client.get("/api/v1/publish/platforms", headers=user_headers),
            200,
        ).json()["data"]
        selected_platform_ids = {target["platform_id"] for target in targets}
        if not selected_platform_ids <= {item["id"] for item in public_platforms}:
            raise AssertionError("Created enabled platforms are missing from the public API")

        publish_payload = {
            "video_id": video_id,
            "title": "Full-stack smoke publish",
            "description": "Two successes and one intentional failure",
            "tags": ["smoke", "frameflow"],
            "targets": targets,
        }
        publish_headers = {**user_headers, "Idempotency-Key": f"smoke-request-{suffix}"}
        published = require_response(
            client.post(
                "/api/v1/publish/tasks",
                headers=publish_headers,
                files={
                    "payload": (None, json.dumps(publish_payload)),
                    "cover": ("cover.png", GATEWAY_UPLOAD_PNG, "image/png"),
                },
            ),
            202,
        ).json()["data"]["tasks"]
        if len({task["id"] for task in published}) != 3:
            raise AssertionError("Three targets did not create three independent publish tasks")

        final_tasks = [
            wait_for_task(
                client,
                f"/api/v1/publish/tasks/{task['id']}",
                user_headers,
                terminal={"success", "failed", "cancelled"},
                timeout_seconds=timeout_seconds,
            )
            for task in published
        ]
        if sorted(task["status"] for task in final_tasks) != ["failed", "success", "success"]:
            raise AssertionError(f"Unexpected mixed publish result: {final_tasks}")

        repeated = require_response(
            client.post(
                "/api/v1/publish/tasks",
                headers=publish_headers,
                files={"payload": (None, json.dumps(publish_payload))},
            ),
            202,
        ).json()["data"]["tasks"]
        if {task["id"] for task in repeated} != {task["id"] for task in published}:
            raise AssertionError("Idempotent HTTP retry created different publish tasks")

        failed_task = next(task for task in final_tasks if task["status"] == "failed")
        failed_account_id = failed_task["account_id"]
        require_response(
            client.patch(
                f"/api/v1/admin/accounts/{failed_account_id}",
                headers=admin_headers,
                json={"extra_config": {"simulate_result": "success"}},
            ),
            200,
        )
        require_response(
            client.post(f"/api/v1/publish/tasks/{failed_task['id']}/retry", headers=user_headers),
            202,
        )
        retried = wait_for_task(
            client,
            f"/api/v1/publish/tasks/{failed_task['id']}",
            user_headers,
            terminal={"success", "failed", "cancelled"},
            timeout_seconds=timeout_seconds,
        )
        if retried["status"] != "success" or retried["retry_count"] != 1:
            raise AssertionError(f"Failed task did not recover after retry: {retried}")

        history = require_response(
            client.get(
                "/api/v1/publish/tasks",
                headers=user_headers,
                params={"video_id": video_id, "page_size": 100},
            ),
            200,
        ).json()
        if history["total"] != 3:
            raise AssertionError(f"Retry or idempotency created duplicate tasks: {history['total']}")
        report("Three-target mixed publish, idempotency and single-task retry passed")

        require_response(
            client.patch(
                f"/api/v1/admin/accounts/{accounts[0]}",
                headers=admin_headers,
                json={"enabled": False},
            ),
            200,
        )
        disabled_payload = {**publish_payload, "targets": [targets[0]]}
        disabled = require_response(
            client.post(
                "/api/v1/publish/tasks",
                headers={**user_headers, "Idempotency-Key": f"disabled-{suffix}"},
                files={"payload": (None, json.dumps(disabled_payload))},
            ),
            400,
        )
        if disabled.json().get("error_code") != "ACCOUNT_DISABLED":
            raise AssertionError(f"Unexpected disabled account error: {disabled.text}")

        accounts_response = require_response(
            client.get("/api/v1/admin/accounts", headers=admin_headers, params={"page_size": 100}),
            200,
        )
        if account_secret in accounts_response.text:
            raise AssertionError("Account list leaked its client secret")
        if model_secret in require_response(
            client.get("/api/v1/admin/video-models", headers=admin_headers, params={"page_size": 100}),
            200,
        ).text:
            raise AssertionError("Model list leaked its API key")
        if model_secret in require_response(
            client.get("/api/v1/admin/model-accounts", headers=admin_headers, params={"page_size": 100}),
            200,
        ).text:
            raise AssertionError("Model account list leaked its API key")

        image_video_id = image_task["video_id"]
        require_response(
            client.delete(f"/api/v1/videos/{image_video_id}", headers=user_headers),
            204,
        )
        require_response(
            client.get(f"/api/v1/videos/{image_video_id}", headers=user_headers),
            404,
        )

        audit = require_response(
            client.get("/api/v1/admin/logs", headers=admin_headers, params={"page_size": 100}),
            200,
        ).json()
        actions = {item["action"] for item in audit["items"]}
        required_actions = {
            "auth.login",
            "generation.create",
            "generation.success",
            "video.delete",
            "publish.create",
            "publish.success",
            "publish.failed",
            "publish.retry",
            "user.create",
            "video_model.create",
            "platform.create",
            "publish_account.create",
        }
        if not required_actions <= actions:
            raise AssertionError(f"Audit actions missing: {sorted(required_actions - actions)}")

        cors = require_response(
            client.options(
                "/api/v1/auth/me",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            ),
            200,
        )
        if cors.headers.get("access-control-allow-origin") != "http://localhost:5173":
            raise AssertionError("CORS did not allow the configured frontend origin")
        report(f"Audit, Secret masking, disabled account and CORS checks passed (user={smoke_user_id})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-password", default="Admin123!")
    parser.add_argument("--user-username", default="user")
    parser.add_argument("--user-password", default="User123!")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    report("Starting real full-stack validation")
    verify_infrastructure()
    verify_seed(args.admin_username)
    run_business_workflow(
        args.base_url,
        args.admin_username,
        args.admin_password,
        args.user_username,
        args.user_password,
        args.timeout,
    )
    report("PASS: full-stack validation completed successfully")


if __name__ == "__main__":
    main()

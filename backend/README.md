# FrameFlow Backend

后端包含 FastAPI API、PostgreSQL ORM/Alembic Migration、Redis/Celery Worker、模型与发布 Adapter、Local Storage、FFmpeg 处理和 pytest 测试。

模型配置使用 `ModelProvider → ModelAccount → VideoModel`，发布配置使用 `PublishPlatform → PublishAccount`。升级已有数据库时运行 `alembic upgrade head`，`20260910_0003` 会自动迁移旧模型配置并保留已有任务数据。

推荐从项目根目录使用 `docker compose up --build` 启动完整系统。若需本机启动、默认账号、环境变量、Adapter 扩展与故障排查，请阅读根目录 `README.md`。

真实 PostgreSQL/Redis/Celery/FFmpeg 一键联调：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-full-stack.ps1
```

常用命令：

```powershell
Copy-Item .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
alembic upgrade head
python -m app.db.init_db
uvicorn app.main:app --reload
```

另开终端启动 Worker：

```powershell
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO --pool=solo
```

## Instagram Reel 发布 PoC

Instagram Adapter 使用 Instagram Login 对应的 `https://graph.instagram.com`，按以下顺序发布：

```text
POST /{ig_user_id}/media
GET  /{container_id}（轮询到 FINISHED）
POST /{ig_user_id}/media_publish
```

平台配置使用 `PublishPlatform.api_base_url`、`api_version` 和 `extra_config`。默认值为 Graph API `v26.0`、5 秒轮询、300 秒处理超时、30 秒 HTTP 超时，并要求公网 HTTPS 视频 URL。账号配置使用 `PublishAccount.ig_user_id` 和加密保存的 Access Token；Adapter 不负责 OAuth 或 Token 刷新。

发布目标的 `overrides` 至少需要：

```json
{
  "video_url": "https://cdn.example.com/video.mp4",
  "caption": "Instagram API PoC",
  "share_to_feed": true
}
```

`publish_type` 使用 `reel`，兼容现有系统的 `video` 值；两者都会发送 `media_type=REELS`。本地路径、localhost、私网地址和默认配置下的 HTTP URL 会在调用 Meta 前被拒绝。

只运行 Instagram Mock 测试：

```powershell
python -m pytest tests\test_instagram_publishing.py -q
```

测试全部使用 `httpx.MockTransport`，不会创建真实 Instagram 内容。真实 PoC 前请先启用 Instagram 平台和账号，并确认 Token 包含 `instagram_business_basic`、`instagram_business_content_publish` 权限。

# FrameFlow AI 视频制作发布平台

FrameFlow 是一个本地可完整联调的 AI 视频生成与多平台发布项目。前端只调用 FastAPI；生成和发布由 Redis + Celery 异步执行；业务数据保存到 PostgreSQL 17，媒体文件保存到本地 Storage。默认 Mock 模型和 Mock 平台不需要任何第三方密钥，也不会向外部平台发送数据。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Element Plus、Axios
- 后端：Python 3.12+、FastAPI、Pydantic、SQLAlchemy 2、Alembic
- 基础设施：PostgreSQL 17、Redis 7、Celery、FFmpeg
- 安全：JWT、Argon2 密码哈希、Fernet 字段级 Secret 加密、后端 RBAC
- 测试：pytest；测试使用隔离的 SQLite 数据库，正式运行配置固定为 PostgreSQL

## 目录

```text
backend/                 FastAPI、ORM、Migration、Celery、Adapter、测试
frontend/                Vue 3 管理端和用户端
storage/                 本地视频、缩略图和上传图片（不进入数据库）
docs/                    架构、数据库和 API 说明
docker-compose.yml       PostgreSQL、Redis、API、Worker、前端
.env.example             Docker Compose 开发配置模板
```

## 最快启动：Docker Compose

环境要求：Docker Desktop（启用 Compose v2）。容器镜像内已安装 FFmpeg，无需主机单独安装。

将仓库下载或克隆到本机后，进入包含 `docker-compose.yml` 的项目根目录。

在项目根目录执行：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

首次启动时 API 容器会自动执行 `alembic upgrade head` 和 Seed。等待 `api`、`worker`、`frontend` 均正常后访问：

- 前端：http://localhost:5173
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- 公开审核视频：`http://localhost:5173/videos-pub/{video_id}`

公开审核视频地址不是前端页面，无需登录，直接以正确的媒体类型返回未删除的视频，并支持 `HEAD` 和 HTTP Range。可用以下命令本地验证：

```powershell
curl.exe -I "http://localhost:5173/videos-pub/<video_id>"
curl.exe -o test.mp4 "http://localhost:5173/videos-pub/<video_id>"
```

X、Instagram、YouTube、Facebook 的服务器无法访问 `localhost`。提交平台审核或在 `video_url` 中使用时，必须先把服务部署到公网 HTTPS 域名，再改用 `https://你的域名/videos-pub/{video_id}`。任何获得该 URL 的人都能读取视频；视频软删除后接口返回 404。

停止服务：

```powershell
docker compose down
```

若希望连同开发数据库卷一起清空，可在确认不需要数据后执行 `docker compose down -v`。

## 一键全栈联调验收

安装并启动 Docker Desktop 后，可让脚本完成构建、启动和真实业务闭环验证：

```powershell
Set-Location 'C:\Users\TB-SD 33\python-project\create_publish'
powershell -ExecutionPolicy Bypass -File .\scripts\verify-full-stack.ps1
```

脚本会实际检查 PostgreSQL 17、JSONB/外键/索引、Redis、Celery Worker 任务注册、FFmpeg/FFprobe，然后通过 FastAPI 完成：

```text
管理员登录与创建用户
→ 文生视频
→ 图生视频
→ Storage 播放与下载
→ 三个独立 Mock 发布任务（2 success + 1 failed）
→ HTTP 幂等重放
→ 只重试失败任务并恢复 success
→ 权限、Secret 脱敏、Audit Log、CORS
```

成功后显示 `PASS`，并保持服务运行，供浏览器继续人工测试。脚本会写入带 `smoke-` 前缀的开发验收数据；如需完全清空，可在测试结束后执行 `docker compose down -v`。

## 默认开发账号

| 角色 | 用户名 | 密码 | 用途 |
| --- | --- | --- | --- |
| 管理员 | `admin` | `Admin123!` | 管理用户、模型、平台、账号、日志 |
| 普通用户 | `user` | `User123!` | 生成、查看、下载、删除和发布自己的视频 |

这些值来自根目录 `.env`，不是代码硬编码。`APP_ENV=production` 时服务会拒绝示例密码；部署前必须更换 JWT、加密密钥、数据库密码和默认账号密码。

Seed 还会创建：

- `Mock Video Model`：支持文生视频、单图生视频，可配置模拟失败。
- `Mock Platform` 与 `默认 Mock 账号`：支持 success / failed / processing 模拟，不访问任何真实第三方接口。

## 本机分别启动前后端

### 1. 启动依赖

安装并启动 PostgreSQL 17、Redis 7 和 FFmpeg。创建数据库和账号：

```sql
CREATE USER video_app WITH PASSWORD 'video_dev_password';
CREATE DATABASE video_platform OWNER video_app;
```

确认命令 `ffmpeg -version`、`ffprobe -version` 和 `redis-cli ping` 可用。

### 2. 后端 API

```powershell
cd backend
Copy-Item .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
alembic upgrade head
python -m app.db.init_db
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

`backend/.env.example` 已使用 `127.0.0.1` 连接本机 PostgreSQL 和 Redis。后端本机进程只读取 `backend/.env`；根目录 `.env` 只由 Compose 注入，避免 `localhost` 与 Docker service name 混用。Migration 是唯一建表入口；Seed 可重复执行，不会重复创建默认记录。

### 3. Celery Worker

另开 PowerShell：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO --pool=solo
```

Windows 本机建议使用 `--pool=solo`。Linux/macOS 可移除该参数或按 CPU 数设置并发。

### 4. 前端

另开 PowerShell：

```powershell
cd frontend
Copy-Item .env.example .env.local
npm ci
npm run dev
```

访问 http://localhost:5173。Vite 将 `/api` 代理到 `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000`。

## 数据库与初始化

```powershell
cd backend
alembic upgrade head
alembic current
python -m app.db.init_db
```

初始 Migration `20260909_0001` 创建 8 张业务表，增量 Migration `20260910_0002` 对齐 ORM 约束和索引命名；`alembic upgrade head` 会自动按顺序执行。数据库结构详见 `docs/database.md`。

## 测试与构建

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest

cd ..\frontend
npm run typecheck
npm run build
```

pytest 使用 `backend/tests/frameflow-test.db` 隔离运行，测试结束后可直接删除；它不改变正式 PostgreSQL 配置。

核心 API 闭环测试位于 `backend/tests/test_end_to_end.py`；真实 Docker 基础设施验收入口为 `scripts/verify-full-stack.ps1`，业务检查脚本为 `backend/scripts/integration_smoke.py`。

## Mock 完整闭环

1. 用普通用户登录，进入“创建视频”。
2. 选择 `Mock Video Model`，输入 Prompt，可选 JPG/PNG/WebP 参考图。
3. API 立即返回任务；Celery 调用 Mock Adapter，并由 FFmpeg 生成真实的本地 MP4、读取元数据和生成缩略图。
4. 在“视频库”查看结果，进入“发布视频”。
5. 选择 `Mock Platform` 和 `默认 Mock 账号`。
6. 系统为每个目标创建独立 PublishTask；Worker 返回 Mock 发布地址；在“发布记录”查看结果。

## 环境变量与安全

完整变量见 `.env.example` 和 `backend/.env.example`。重点配置：

- `DATABASE_URL`：必须是 PostgreSQL 连接。
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`：Redis 地址。
- `JWT_SECRET_KEY`：JWT 签名密钥。
- `SECRET_ENCRYPTION_KEY`：模型 API Key 和平台 Token 的字段级加密密钥。
- `STORAGE_PATH`：本地媒体目录；数据库仅保存 key、URL 和元数据。
- `CORS_ORIGINS`：逗号分隔的明确来源，生产环境不要配置 `*`。
- `GENERATION_POLL_INTERVAL` / `GENERATION_TIMEOUT` / `CELERY_MAX_RETRIES`：轮询、超时和重试。

API 只返回 Secret 是否已配置及脱敏值，不返回原文；结构化日志不记录密码、API Key 或 Token。生产环境建议进一步使用云 Secrets Manager/KMS，并将 `STORAGE_TYPE` 扩展到 S3/MinIO。

## Adapter 扩展

视频模型采用 `ModelProvider → ModelAccount → VideoModel` 三层配置。已注册 Veo 3.1、Runway Gen-4.5、Seedance 2.5、Luma Ray 3.2、MiniMax Hailuo 2.3 和 Mock Adapter。MiniMax 模型目录默认启用，但只有管理员为账号配置 API Key 后才会真正提交；其他真实模板默认停用。API Key、Token、Project/Region 只属于账号层，具体模型只保存 Model ID、capabilities 与 request defaults。Service 与具体厂商无耦合。

## MiniMax Hailuo 2.3

接入依据 MiniMax Open Platform 的 [Text-to-Video](https://platform.minimax.io/docs/api-reference/video-generation-t2v)、[Image-to-Video](https://platform.minimax.io/docs/api-reference/video-generation-i2v)、[任务查询](https://platform.minimax.io/docs/api-reference/video-generation-query) 和 [视频下载](https://platform.minimax.io/docs/api-reference/video-generation-download) 文档。先在 MiniMax Open Platform 注册并开通 Pay-as-you-go Access，再到 Account Management 创建 API Key。

种子数据会建立以下关系：

```text
MiniMax (Provider, bearer_token)
└── MiniMax PoC Account (Account, API Key 由管理员写入)
    └── MiniMax Hailuo 2.3 (Model, minimax_hailuo23)
```

账号凭证通过 `PATCH /api/v1/admin/model-accounts/{id}` 的 `api_key` 字段保存；数据库只保存加密值，查询仅返回脱敏值。`POST /api/v1/admin/model-accounts/{id}/test` 只检查启用状态、HTTPS Base URL、API Key 和客户端初始化条件，不访问 MiniMax，也不会产生费用；返回中的 `real_api_verified` 固定为 `false`。

Hailuo 2.3 支持文生视频和单首帧图生视频。时长/分辨率组合为 `6s + 768P`、`6s + 1080P`、`10s + 768P`；前后端均从模型 `capabilities` 读取约束。图生视频支持 JPG/JPEG/PNG/WebP、小于 20 MB、短边大于 300 像素、宽高比 0.4–2.5；本地 Storage 图片会转为 Base64 Data URL，公网 URL 也可直接传递。

异步链路为：FastAPI 创建本地任务 → Celery 调用 `POST /v1/video_generation` → 保存 `task_id` → 按间隔重新调度并调用 `GET /v1/query/video_generation?task_id=...` → 成功后用 `GET /v1/files/retrieve?file_id=...` 获取下载地址 → 流式下载 MP4 → Storage → FFmpeg 元数据和缩略图 → 创建 Video。MiniMax 轮询任务不会在 Worker 中 busy loop；相关配置为：

```env
MINIMAX_API_BASE_URL=https://api.minimax.io
MINIMAX_POLL_INTERVAL_SECONDS=10
MINIMAX_GENERATION_TIMEOUT_SECONDS=900
MINIMAX_HTTP_TIMEOUT_SECONDS=60
```

本次接入仅使用 `httpx.MockTransport` 验证官方完整链路，没有执行真实 MiniMax 生成。充值后如需首次真实 PoC，请先配置账号 API Key 并重启 API/Worker，然后在页面选择 `MiniMax Hailuo 2.3`，使用简单 Prompt、`6 秒`、`768P` 创建一条文生视频任务；确认前请勿运行该步骤。

发布平台采用 `PublishPlatform → PublishAccount` 分层。已注册 X、Instagram、YouTube、Facebook 和 Mock Adapter，并通过平台 `capabilities` 描述真实能力。四个真实平台模板默认停用；没有经官方凭证端到端验证时会明确拒绝外部写入，不会伪造发布成功。

## 常见问题

- 生成任务一直 pending：确认 Redis 与 Celery Worker 正常，Worker 能读写同一个 `storage/`。
- 生成失败并提示 FFmpeg：确认 `ffmpeg` 与 `ffprobe` 在 PATH，或配置 `FFMPEG_BINARY` / `FFPROBE_BINARY`。
- API 启动时报数据库错误：确认 PostgreSQL 17 已启动，账号、数据库和 `DATABASE_URL` 一致，再运行 Migration。
- 前端出现 401：登录态已失效，重新登录；403 表示后端权限校验拒绝当前账号。
- 修改 Secret 时留空：表示保留旧值；列表和详情永远不会回传原文。
- 真实平台不能发布：第一阶段只承诺 Mock 闭环；未提供凭证且未核验官方 API 时不会模拟成真实成功。

更多信息见 [架构说明](docs/architecture.md)、[数据库说明](docs/database.md)、[API 清单](docs/api.md) 和 [全项目联调测试](docs/integration-testing.md)。


访问：
- 前端：http://localhost:5173
- API 文档：http://localhost:8000/docs
默认应用账号：
- 管理员：admin / Admin123!
- 普通用户：user / User123!


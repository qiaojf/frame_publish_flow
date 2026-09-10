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

在项目根目录执行：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

首次启动时 API 容器会自动执行 `alembic upgrade head` 和 Seed。等待 `api`、`worker`、`frontend` 均正常后访问：

- 前端：http://localhost:5173
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

停止服务：

```powershell
docker compose down
```

若希望连同开发数据库卷一起清空，可在确认不需要数据后执行 `docker compose down -v`。

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

`backend/.env.example` 已使用 `127.0.0.1` 连接本机 PostgreSQL 和 Redis。Migration 是唯一建表入口；Seed 可重复执行，不会重复创建默认记录。

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

初始 Migration 位于 `backend/alembic/versions/20260909_0001_initial.py`，一次性创建 8 张业务表及外键、唯一约束和索引。数据库结构详见 `docs/database.md`。

## 测试与构建

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest

cd ..\frontend
npm run typecheck
npm run build
```

pytest 使用 `backend/tests/frameflow-test.db` 隔离运行，测试结束后可直接删除；它不改变正式 PostgreSQL 配置。

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

视频模型：实现 `backend/app/adapters/video_models/base.py` 中的 `VideoModelAdapter`，在 `factory.py` 注册新的 `adapter_type`，再由管理员配置模型能力。Service 与具体厂商无耦合。

发布平台：实现 `backend/app/adapters/publishing/base.py` 中的 `PublishPlatformAdapter`，在 `factory.py` 注册，并通过平台 `capabilities` 描述真实能力。YouTube、X、Instagram、WhatsApp 当前只有明确报错的未配置占位，不伪造发布成功；接入前应依据当时官方 API、账号权限和用户授权实现。

## 常见问题

- 生成任务一直 pending：确认 Redis 与 Celery Worker 正常，Worker 能读写同一个 `storage/`。
- 生成失败并提示 FFmpeg：确认 `ffmpeg` 与 `ffprobe` 在 PATH，或配置 `FFMPEG_BINARY` / `FFPROBE_BINARY`。
- API 启动时报数据库错误：确认 PostgreSQL 17 已启动，账号、数据库和 `DATABASE_URL` 一致，再运行 Migration。
- 前端出现 401：登录态已失效，重新登录；403 表示后端权限校验拒绝当前账号。
- 修改 Secret 时留空：表示保留旧值；列表和详情永远不会回传原文。
- 真实平台不能发布：第一阶段只承诺 Mock 闭环；未提供凭证且未核验官方 API 时不会模拟成真实成功。

更多信息见 [架构说明](docs/architecture.md)、[数据库说明](docs/database.md) 和 [API 清单](docs/api.md)。

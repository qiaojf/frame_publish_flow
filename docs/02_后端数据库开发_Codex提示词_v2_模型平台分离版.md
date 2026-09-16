# 02_后端数据库开发_Codex提示词

## 一、你的角色

你是一名高级 Python 后端架构师、FastAPI 开发工程师和 PostgreSQL 数据库设计工程师。

你的任务是完成“AI 视频制作发布平台”的：

```text
后端
+
数据库
+
异步任务
+
模型适配层
+
发布适配层
+
文件存储
+
权限
+
测试
```

本提示词已经包含数据库设计要求。

**不要再额外创建另一套独立数据库设计。**

数据库必须与：

```text
SQLAlchemy ORM
Pydantic Schema
Service
API
Celery Task
```

统一设计。

---

# 二、固定技术栈

必须使用：

```text
Python
FastAPI
SQLAlchemy
Alembic
Pydantic
PostgreSQL 17
Redis
Celery
JWT
FFmpeg
```

文件存储：

开发阶段：

```text
Local Storage
```

同时抽象：

```text
MinIO / S3 Compatible Storage
```

禁止：

- SQLite 代替 PostgreSQL 作为主要数据库
- MongoDB
- 把视频 Blob 存 PostgreSQL
- 把图片 Blob 存 PostgreSQL
- 长时间阻塞 HTTP 请求等待 AI 视频生成完成
- 让前端直接调用真实 AI / 社交平台接口

---

# 三、核心业务

系统两个核心闭环：

## 视频生成

```text
用户
↓
Prompt
+
可选图片
↓
选择模型
↓
创建生成任务
↓
Celery
↓
VideoModelAdapter
↓
AI 模型
↓
视频结果
↓
Storage
↓
Video
```

## 视频发布

```text
Video
↓
选择多个平台
↓
一个平台一个 PublishTask
↓
Celery
↓
PublishPlatformAdapter
↓
第三方平台
↓
独立记录结果
```

---

# 四、角色

只包含：

```text
admin
user
```

## user

可以：

- 登录
- 生成视频
- 查看自己的任务
- 查看自己的视频
- 下载自己的视频
- 删除自己的视频
- 重新生成
- 发布自己的视频
- 查看自己的发布记录
- 重试自己的失败发布任务

## admin

拥有 user 全部权限，并可：

- 用户管理
- 视频模型管理
- 发布平台管理
- 发布账号管理
- 查看操作日志

---

# 五、权限原则

权限必须在后端实际校验。

禁止只依靠前端隐藏菜单。

普通用户不能：

- 查看别人视频
- 删除别人视频
- 发布别人视频
- 查看别人生成任务
- 查看别人发布任务
- 调用管理员 API

管理员 API 无权限必须：

```text
403 Forbidden
```

未认证：

```text
401 Unauthorized
```

---

# 六、认证

使用 JWT。

至少实现：

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

密码：

- 使用安全 Hash
- 禁止明文
- 推荐 bcrypt / argon2

JWT Secret：

从 `.env` 获取。

禁止硬编码。

---

# 七、项目目录

推荐：

```text
backend/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── video_models.py
│   │   ├── generation.py
│   │   ├── videos.py
│   │   ├── platforms.py
│   │   ├── publishing.py
│   │   └── logs.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── permissions.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   │
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── adapters/
│   │   ├── video_models/
│   │   └── publishing/
│   ├── tasks/
│   ├── storage/
│   └── utils/
│
├── alembic/
├── tests/
├── requirements.txt
├── alembic.ini
└── README.md
```

允许小幅调整，但必须保持：

```text
API
Service
Adapter
Model
Schema
Task
Storage
```

职责清晰。

---

# 八、数据库设计原则

数据库和后端一起设计，不单独开发。

至少包含以下表：

```text
users
video_models
video_generation_tasks
videos
publish_platforms
publish_accounts
publish_tasks
audit_logs
```

可根据需要增加：

```text
uploaded_assets
refresh_tokens
```

不要过度建表。

所有核心表：

- 主键
- created_at
- updated_at（适用时）
- 外键
- 必要索引
- 明确状态字段

---

# 九、users

建议字段：

```text
id
username
display_name
email
password_hash
role
enabled
last_login_at
created_at
updated_at
```

约束：

- username 唯一
- email 可选，但存在时建议唯一
- role 枚举：admin / user
- enabled bool

索引：

- username
- role
- enabled

---

# 十、模型配置分层：Provider / Account / Model

模型配置必须拆成三层：

```text
ModelProvider
    ↓
ModelAccount
    ↓
VideoModel
```

这样同一个接入账号可以复用给多个模型，例如：

```text
Runway Developer API
└── Company Production Account
    ├── Runway Gen-4.5
    └── Seedance 2.5
```

不要在每一个 `video_models` 记录里重复保存 API Key。

## 十.1 model_providers

表示“通过哪个模型服务提供商接入”。

例如：

```text
Google Vertex AI
Runway Developer API
Luma
MiniMax
Mock Provider
```

建议字段：

```text
id
name
code
adapter_family
default_api_base_url
default_api_version
auth_type
provider_capabilities JSONB
extra_config JSONB
enabled
created_at
updated_at
```

`code` 示例：

```text
google_vertex
runway
luma
minimax
mock
```

`auth_type` 示例：

```text
api_key
bearer_token
google_adc
service_account
oauth2
```

Provider 层只保存提供商公共配置，不保存具体模型时长、分辨率等能力。

## 十.2 model_accounts

表示 Provider 下的一套实际接入账号 / 凭证。

关系：

```text
ModelProvider
    ↓
ModelAccount
```

建议字段：

```text
id
provider_id
name
account_identifier
api_base_url
api_version
api_key
access_token
project_id
region
service_account_ref
credential_extra JSONB
extra_config JSONB
enabled
created_at
updated_at
```

示例：

```text
Runway Developer API
├── Company Production
└── Company Test

Google Vertex AI
└── Terabox GCP Project
```

敏感字段必须脱敏，禁止通过普通 API 或日志返回完整值。

## 十.3 video_models

表示具体可被用户选择的视频模型。

关系：

```text
ModelAccount
    ↓
VideoModel
```

建议字段：

```text
id
model_account_id
name
code
model_id
adapter_type
supports_text_to_video
supports_image_to_video
capabilities JSONB
request_defaults JSONB
extra_config JSONB
enabled
created_at
updated_at
```

例如：

```text
Runway / Company Production
├── Gen-4.5
└── Seedance 2.5

Google Vertex / Terabox GCP
└── Veo 3.1
```

其中：

- `ModelProvider`：定义接入服务
- `ModelAccount`：保存账号和凭证
- `VideoModel`：保存具体模型 ID、能力和默认参数

这三层职责不得混在一张表中。

# 十一、video_generation_tasks

每次生成建立独立任务。

字段：

```text
id
user_id
model_id

generation_type

prompt
source_image_url

duration
aspect_ratio
resolution

provider_task_id

status
progress

error_code
error_message

result_video_id

created_at
started_at
completed_at
updated_at
```

generation_type：

```text
text_to_video
image_to_video
```

status：

```text
pending
processing
success
failed
cancelled
timeout
```

索引：

```text
user_id
model_id
status
created_at
provider_task_id
```

---

# 十二、videos

生成成功形成独立视频资产。

字段至少：

```text
id
owner_id
generation_task_id

title
description

video_url
thumbnail_url

storage_key
thumbnail_storage_key

file_size
duration
width
height
mime_type

created_at
updated_at
```

约束：

- 一个 generation_task 最多关联一个主要生成视频
- owner_id 建索引
- generation_task_id 建索引

删除策略：

不要随意 Cascade 删除所有历史发布记录。

根据实现设计软删除或明确资源清理策略。

---

# 十三、publish_platforms

表示平台本身，例如：

```text
YouTube
X
Instagram
Facebook
Mock Platform
```

字段：

```text
id
name
code
adapter_type
api_base_url
capabilities JSONB
extra_config JSONB
enabled
created_at
updated_at
```

例如 capabilities：

```json
{
  "supports_video": true,
  "fields": ["title", "description", "tags"],
  "requires_account": true
}
```

code 唯一。

---

# 十四、publish_accounts

平台和账号必须拆开。

关系：

```text
PublishPlatform
    ↓
PublishAccount
```

字段：

```text
id
platform_id
name
account_identifier

client_id
client_secret
access_token
refresh_token
token_expires_at

extra_config JSONB

enabled

created_at
updated_at
```

例如：

```text
YouTube
├── 公司官方频道
└── 产品频道
```

敏感字段：

- 不得明文输出 API Response
- 列表接口只返回 masked 值
- 日志禁止记录原文

---

# 十五、publish_tasks

核心原则：

```text
一个平台 = 一个独立 PublishTask
```

禁止设计：

```text
一个 PublishTask 保存多个平台数组
```

字段至少：

```text
id
video_id
user_id
platform_id
account_id

status

title
content
tags

platform_overrides JSONB

platform_post_id
platform_post_url

idempotency_key

error_code
error_message

retry_count

created_at
started_at
completed_at
updated_at
```

状态：

```text
pending
publishing
success
failed
cancelled
```

索引：

```text
video_id
user_id
platform_id
account_id
status
created_at
idempotency_key
```

---

# 十六、audit_logs

字段：

```text
id
user_id
action
resource_type
resource_id
result
ip_address
message
created_at
```

至少记录：

- 登录
- 生成任务创建
- 生成成功
- 生成失败
- 删除视频
- 发布任务创建
- 发布成功
- 发布失败
- 重试发布
- 用户管理
- 模型配置
- 平台配置
- 账号配置

禁止记录：

```text
密码
完整 API Key
Client Secret
Access Token
Refresh Token
```

---

# 十七、Alembic

必须：

- 建立 initial migration
- 所有表通过 migration 创建
- 不依赖手工 SQL 建表
- migration 可重复在空数据库执行

提供：

```bash
alembic upgrade head
```

初始化命令说明。

---

# 十八、Seed 数据

开发环境初始化：

## 默认管理员

例如：

```text
username: admin
```

密码从：

```text
.env
```

或开发配置获取。

不要把生产默认密码写死。

---

## Mock Video Model

自动创建：

```text
Mock Model Provider
Mock Model Account
Mock Video Model
```

其中 Mock Video Model 支持：

```text
text_to_video
image_to_video
```

---

## Mock Platform

自动创建：

```text
Mock Platform
```

并创建一个默认 Mock Account。

确保无任何真实第三方 Key 也能联调整个流程。

---

# 十九、视频生成判断

前端不指定 generation_type 也可以。

后端根据：

```text
prompt
image
```

自动判断。

## 文生视频

```text
prompt != empty
image == empty
```

结果：

```text
text_to_video
```

## 图生视频

```text
prompt != empty
image != empty
```

结果：

```text
image_to_video
```

如果：

```text
prompt == empty
```

返回：

```text
400 / 422
```

---

# 二十、模型能力校验

在创建任务前：

后端必须根据模型能力检查：

- 是否 enabled
- 是否支持 text_to_video
- 是否支持 image_to_video
- duration 是否允许
- aspect_ratio 是否允许
- resolution 是否允许
- image 数量是否允许

禁止只依赖前端校验。

---

# 二十一、VideoModelAdapter

建立抽象接口。

建议：

```python
class VideoModelAdapter(ABC):

    async def create_text_to_video(self, ...):
        ...

    async def create_image_to_video(self, ...):
        ...

    async def get_task_status(self, ...):
        ...

    async def get_result(self, ...):
        ...
```

建立：

```text
ModelAdapterFactory
```

根据：

```text
adapter_type
```

加载对应实现。

业务 Service 不直接判断具体厂商。

禁止：

```python
if provider == "x":
    ...
elif provider == "y":
    ...
```

散落在业务逻辑。

---

# 二十二、MockVideoModelAdapter

必须实现。

行为可以：

```text
提交任务
↓
pending
↓
processing
↓
success
```

可以使用本地示例 MP4 作为最终视频。

Mock 需要支持：

- 文生视频
- 图生视频
- 成功
- 可配置模拟失败

用于：

- 开发
- 自动测试
- 联调

---

# 二十三、异步任务

必须使用：

```text
Redis + Celery
```

视频生成 HTTP API：

只负责：

```text
参数校验
↓
创建 DB 任务
↓
发送 Celery Task
↓
立即返回 task_id
```

禁止：

HTTP 请求一直等待 AI 完成。

Celery 负责：

```text
调用模型
↓
保存 provider_task_id
↓
查询状态
↓
成功
↓
下载视频
↓
保存 Storage
↓
FFmpeg 元数据
↓
缩略图
↓
创建 Video
↓
更新 GenerationTask
```

---

# 二十四、任务轮询策略

第三方模型如果是异步 API：

Celery 内部应合理处理状态查询。

不要无限 busy loop。

使用：

- delay
- retry
- 定时轮询
- 最大超时

最大任务时间和轮询间隔通过配置控制。

---

# 二十五、Storage 抽象

建立：

```python
class StorageBackend:
    def save(...)
    def delete(...)
    def get_url(...)
```

至少实现：

```text
LocalStorageBackend
```

为：

```text
S3StorageBackend
MinIOStorageBackend
```

预留扩展。

视频和图片数据库只保存：

- storage_key
- URL
- 元数据

---

# 二十六、文件上传

图片上传支持：

```text
jpg
jpeg
png
webp
```

限制：

- MIME
- 扩展名
- 文件大小

最大值从 `.env` 配置。

文件名不要直接信任用户原始文件名。

使用安全唯一 key。

---

# 二十七、FFmpeg

生成成功后至少：

- 读取 duration
- width
- height
- MIME / format
- 生成缩略图

如果本地没有 FFmpeg：

应给出清楚错误，而不是静默失败。

README 说明依赖。

---

# 二十八、视频 API

至少：

```text
GET    /api/v1/videos
GET    /api/v1/videos/{id}
DELETE /api/v1/videos/{id}
```

必要时：

```text
GET /api/v1/videos/{id}/download
```

普通用户只能操作自己的视频。

管理员可以按规则访问全部。

---

# 二十九、生成 API

至少：

```text
POST /api/v1/generation/tasks
GET  /api/v1/generation/tasks
GET  /api/v1/generation/tasks/{id}
```

POST 支持：

```text
multipart/form-data
```

包含：

```text
prompt
model_id
image?
duration?
aspect_ratio?
resolution?
```

返回 task。

---

# 三十、发布逻辑

发布接口接收：

- video_id
- 公共标题
- 公共内容
- tags
- 多个平台选择
- 每个平台 account_id
- 平台覆盖内容

例如请求：

```json
{
  "video_id": "xxx",
  "title": "公共标题",
  "content": "公共内容",
  "tags": ["AI", "video"],
  "targets": [
    {
      "platform_id": "youtube",
      "account_id": "acc1",
      "overrides": {}
    },
    {
      "platform_id": "x",
      "account_id": "acc2",
      "overrides": {
        "content": "X 专用文字"
      }
    }
  ]
}
```

后端必须为每个 target 创建独立 PublishTask。

---

# 三十一、PublishPlatformAdapter

抽象：

```python
class PublishPlatformAdapter(ABC):

    async def publish_video(self, ...):
        ...

    async def get_publish_status(self, ...):
        ...

    async def refresh_token(self, ...):
        ...
```

建立：

```text
PublishAdapterFactory
```

预留：

```text
YouTubeAdapter
XAdapter
InstagramAdapter
FacebookAdapter
MockPublishAdapter
```

真实平台实现前必须查对应平台当前官方 API。

禁止伪造不存在的接口能力。

---

# 三十二、Facebook 特别处理

不要假设 Facebook 一定支持和 YouTube/X 完全一样的“公开视频发布”。

必须：

- 通过 Adapter Capability 表达实际能力
- 如果平台 API 只能发送消息或媒体给特定会话/号码，应按真实能力实现
- 不得伪造“公开社交发布成功”

其他平台同理。

---

# 三十三、MockPublishAdapter

必须实现。

支持模拟：

```text
success
failed
processing
```

返回：

```text
mock platform_post_id
mock platform_post_url
```

用于联调。

---

# 三十四、发布异步任务

流程：

```text
POST publish
↓
创建多个 PublishTask
↓
Celery
↓
逐个任务执行
↓
PublishPlatformAdapter
↓
更新每个任务状态
```

平台互相独立。

例如：

```text
YouTube success
Instagram success
X failed
```

不得把成功的两个回滚。

---

# 三十五、失败重试

接口：

```text
POST /api/v1/publish/tasks/{id}/retry
```

只能：

- retry failed task
- 重新运行当前平台任务

不能：

- 重建其他 success 平台任务

需要做：

- 权限校验
- 状态校验
- 幂等校验

---

# 三十六、幂等性

避免：

```text
双击
客户端重试
Celery 重试
网络超时
```

导致重复发布。

为 publish task 生成：

```text
idempotency_key
```

合理实现唯一性策略。

对于已 success 的同一任务：

不要因为 Celery retry 再发一次。

---

# 三十七、自动重试策略

可以自动重试：

```text
网络超时
临时性 5xx
429（尊重 Retry-After）
```

不应无限重试：

```text
400
401
403
业务参数错误
账号未授权
内容不符合平台规则
```

最大重试次数配置化。

---

# 三十八、发布平台和账号 API

普通用户：

```text
GET /api/v1/publish/platforms
```

只返回：

- enabled 平台
- 可使用账号
- capabilities
- 不含 Secret

管理员：

```text
/api/v1/admin/platforms
/api/v1/admin/accounts
```

支持 CRUD。

---

# 三十九、管理员模型 API

管理员：

```text
/api/v1/admin/video-models
```

支持：

- 列表
- 创建
- 更新
- 启用
- 禁用
- 删除
- 测试连接（若实现）

普通用户：

```text
GET /api/v1/video-models
```

只返回 enabled 模型和安全字段。

---

# 四十、Secret 安全

敏感信息至少包括：

```text
api_key
client_secret
access_token
refresh_token
jwt_secret
```

要求：

- 不在日志输出
- API 列表不返回原文
- 前端编辑时返回 masked
- `.env` 不提交真实值
- Git 仓库只提交 `.env.example`

如能合理实现字段级加密，可实现；如果暂不实现，至少保证不暴露，并在 README 中说明生产环境建议使用 Secrets Manager / KMS。

---

# 四十一、统一返回

建议：

成功：

```json
{
  "success": true,
  "data": {},
  "message": null
}
```

失败：

```json
{
  "success": false,
  "data": null,
  "message": "错误信息",
  "error_code": "XXX"
}
```

分页：

```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

保持整个后端一致。

---

# 四十二、异常处理

统一处理：

```text
400
401
403
404
409
422
500
```

第三方 API 原始 Stack Trace：

只进入服务端日志。

前端得到：

- 可理解 message
- error_code

---

# 四十三、CORS

通过 `.env` 配置：

```text
CORS_ORIGINS
```

开发时允许前端地址。

不要生产环境直接 `*`。

---

# 四十四、环境配置

`.env.example` 至少：

```text
APP_ENV=
APP_HOST=
APP_PORT=

DATABASE_URL=

REDIS_URL=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=

JWT_SECRET_KEY=
JWT_EXPIRE_MINUTES=

STORAGE_TYPE=local
STORAGE_PATH=

UPLOAD_MAX_SIZE_MB=

GENERATION_POLL_INTERVAL=
GENERATION_TIMEOUT=

CELERY_MAX_RETRIES=

CORS_ORIGINS=

DEFAULT_ADMIN_USERNAME=
DEFAULT_ADMIN_PASSWORD=
```

---

# 四十五、Docker Compose

项目根目录提供：

```text
docker-compose.yml
```

至少启动：

```text
PostgreSQL
Redis
```

可选：

```text
MinIO
```

后端和 Worker 可以：

- Docker 启动
- 或本地启动

README 必须说明。

---

# 四十六、日志

使用结构化日志。

至少记录：

- request id
- task id
- user id（可用时）
- 关键业务动作
- 第三方 provider
- 错误

不要记录 Secret。

---

# 四十七、测试

使用：

```text
pytest
```

至少覆盖：

## Auth

- 登录成功
- 登录失败
- disabled user
- admin 权限
- user 访问 admin 403

## Generation

- 只有文字 -> text_to_video
- 文字 + 图片 -> image_to_video
- 空 Prompt 拒绝
- 模型不支持类型
- 模型 disabled
- 参数不符合 capabilities
- Mock Adapter success
- Mock Adapter failure

## Video

- owner 可查看
- 非 owner 403/404
- 删除权限
- 视频创建成功

## Publish

- 多 target -> 多 PublishTask
- 每个平台独立状态
- success + failed 混合
- retry 只重试 failed
- success 不重复发布
- 幂等逻辑

## Admin

- 用户 CRUD
- 模型 CRUD
- 平台 CRUD
- 账号 CRUD
- Secret 不泄露

---

# 四十八、第一阶段真实平台策略

本阶段优先完成：

```text
架构
+
Mock
+
可插拔 Adapter
```

对于：

```text
YouTube
X
Instagram
Facebook
```

如果没有真实账号/API Key：

不要阻塞项目。

至少完成：

- Adapter 接口
- 配置模型
- capability
- 参数结构
- Mock
- README 接入说明

如果真实凭证存在并明确允许测试，可以接入真实 Adapter。

---

# 四十九、第一阶段不做

不要实现：

- 在线视频剪辑
- AI 数字人
- AI 配音
- 自动字幕
- 自动 Prompt
- 自动脚本
- 定时发布
- 评论管理
- 私信管理
- BI
- 审批
- 微服务
- Kubernetes

---

# 五十、开发顺序

严格：

## Phase 1

- 项目骨架
- 配置
- PostgreSQL
- Redis
- SQLAlchemy
- Alembic

## Phase 2

- users
- JWT
- 权限
- seed admin

## Phase 3

- video_models
- VideoModelAdapter
- MockVideoModelAdapter

## Phase 4

- generation task
- Celery
- Storage
- FFmpeg
- Video

## Phase 5

- publish_platforms
- publish_accounts
- PublishPlatformAdapter
- MockPublishAdapter

## Phase 6

- PublishTask
- 多平台任务拆分
- Celery 发布
- retry
- 幂等

## Phase 7

- Audit Log
- Admin APIs
- 完整测试

---

# 五十一、完整本地闭环必须跑通

没有任何真实第三方 API Key 时：

必须能：

```text
admin 登录
↓
创建普通用户
↓
普通用户登录
↓
输入 Prompt
↓
可选图片
↓
选择 Mock Video Model
↓
创建生成任务
↓
Celery 执行
↓
生成 Video
↓
查看 Video
↓
选择 Mock Platform
↓
创建 PublishTask
↓
Celery 执行
↓
发布成功
↓
查看 Publish History
```

---

# 五十二、验收标准

## Database

- [ ] PostgreSQL 正常
- [ ] Alembic 正常
- [ ] Migration 可从空库执行
- [ ] Seed 正常
- [ ] FK 正常
- [ ] 索引合理

## Auth

- [ ] JWT 正常
- [ ] user/admin 权限正确
- [ ] 密码 Hash

## Generation

- [ ] 文生视频判断
- [ ] 图生视频判断
- [ ] 模型 capabilities 校验
- [ ] Celery 异步
- [ ] Mock Model
- [ ] Video 资产保存

## Publish

- [ ] 平台/账号分离
- [ ] 多平台 -> 多任务
- [ ] 独立状态
- [ ] retry
- [ ] 幂等
- [ ] Mock Publish

## Security

- [ ] Secret 不返回原文
- [ ] Secret 不进日志
- [ ] 普通用户无后台权限
- [ ] 用户不能操作别人的资源

## Tests

- [ ] pytest 通过
- [ ] 核心链路测试存在

---

# 五十三、README

必须包含：

```text
项目简介
技术栈
目录
环境要求
.env
PostgreSQL 启动
Redis 启动
Alembic Migration
Seed
FastAPI 启动
Celery Worker 启动
FFmpeg 安装
Mock Model
Mock Platform
pytest
真实模型 Adapter 扩展方法
真实发布平台 Adapter 扩展方法
常见问题
```

---

# 五十四、最终交付报告

完成后必须输出：

1. 已完成模块
2. 数据库表
3. Migration
4. Seed
5. API 清单
6. Celery Task
7. VideoModelAdapter
8. PublishPlatformAdapter
9. Mock 实现
10. 文件存储
11. 安全措施
12. pytest 结果
13. 启动命令
14. 默认开发管理员
15. 尚未接入的真实第三方平台及原因

禁止仅回答“完成”。

---

# 五十五、最重要的后端原则

始终保持：

```text
API
↓
Service
↓
Adapter / Repository
↓
PostgreSQL / Third-party API
```

以及：

```text
数据库结构
=
SQLAlchemy
=
Alembic
=
Pydantic
=
业务代码
```

这五部分必须一致。

**不要执行独立的数据库设计任务去重新定义第二套数据库。**

# 五十六、真实视频模型 Adapter 设计（新增）

本阶段需要为以下 5 个模型建立可插拔真实 Adapter：

```text
Google Veo 3.1
Runway Gen-4.5
ByteDance Seedance 2.5
Luma Ray 3.2
MiniMax Hailuo 2.3
```

统一原则：

- 无真实 API Key 时也必须完成 Adapter、配置结构、参数校验、Mock 测试。
- 不得用 Mock 成功结果冒充真实第三方调用成功。
- 模型参数必须通过数据库 `capabilities JSONB` 管理，前端不得写死。
- Service 层不得直接依赖具体厂商 SDK。
- Adapter 负责把平台统一参数映射成厂商请求参数。

统一接口建议：

```python
class VideoModelAdapter(ABC):
    async def create_text_to_video(self, request, model_config): ...
    async def create_image_to_video(self, request, model_config): ...
    async def get_task_status(self, provider_task_id, model_config): ...
    async def get_result(self, provider_task_id, model_config): ...
    async def cancel_task(self, provider_task_id, model_config): ...
    async def test_connection(self, model_config): ...
```

统一内部结果：

```python
class ProviderTaskResult:
    provider_task_id: str
    status: str
    progress: int | None
    result_url: str | None
    error_code: str | None
    error_message: str | None
    raw_response: dict | None
```

# 五十七、真实模型配置架构：Provider / Account / Model

真实模型接入也必须遵守同样的三层结构：

```text
ModelProvider
    ↓
ModelAccount
    ↓
VideoModel
    ↓
VideoModelAdapter
```

推荐映射：

```text
Google Vertex AI
└── Terabox GCP Account
    └── Google Veo 3.1

Runway Developer API
└── Company Runway Account
    ├── Runway Gen-4.5
    └── Seedance 2.5

Luma
└── Company Luma Account
    └── Luma Ray 3.2

MiniMax
└── Company MiniMax Account
    └── MiniMax Hailuo 2.3
```

Provider 层保存：

```text
name
code
default_api_base_url
default_api_version
auth_type
adapter_family
```

Account 层保存：

```text
provider_id
账号名称
api_base_url / api_version（可覆盖 Provider 默认值）
API Key / Access Token
Project ID
Region
Service Account 引用
其他账号级认证信息
enabled
```

VideoModel 层保存：

```text
model_account_id
name
code
model_id
adapter_type
supports_text_to_video
supports_image_to_video
capabilities JSONB
request_defaults JSONB
extra_config JSONB
enabled
```

重要原则：

- API Key 不放在 `video_models`
- Project / Region 等账号级参数不放在 `video_models`
- 同一个 ModelAccount 可以挂多个 VideoModel
- 模型的时长、分辨率、比例、FPS 等放在 `capabilities JSONB`
- 前端只读取 VideoModel 的安全字段与 capabilities

# 五十八、统一 capabilities JSONB

建议统一结构：

```json
{
  "text_to_video": true,
  "image_to_video": true,
  "supports_first_frame": true,
  "supports_last_frame": false,
  "supports_reference_image": true,
  "supports_reference_video": false,
  "supports_reference_audio": false,
  "native_audio": false,
  "duration_mode": "enum",
  "durations": [5, 10],
  "duration_min": null,
  "duration_max": null,
  "resolutions": ["720p", "1080p"],
  "aspect_ratios": ["16:9", "9:16"],
  "fps": [24],
  "max_images": 1,
  "max_image_size_mb": 20,
  "max_prompt_length": 2000,
  "max_outputs_per_request": 1,
  "extra": {}
}
```

`duration_mode=enum` 时从 `durations` 选择；`range` 时使用 `duration_min` / `duration_max`。

# 五十九、Google Veo 3.1 Adapter

类名：

```text
GoogleVeo31Adapter
```

建议支持：

```text
veo-3.1-generate-001
veo-3.1-fast-generate-001
```

管理员配置：

```text
provider = google
adapter_type = google_veo31
model_id
project_id
region
auth_type = google_service_account
```

建议 capabilities：

```json
{
  "text_to_video": true,
  "image_to_video": true,
  "supports_first_frame": true,
  "supports_last_frame": true,
  "supports_reference_image": true,
  "native_audio": true,
  "duration_mode": "enum",
  "durations": [4, 6, 8],
  "resolutions": ["720p", "1080p", "4k"],
  "aspect_ratios": ["16:9", "9:16"],
  "fps": [24],
  "max_images": 1,
  "max_image_size_mb": 20,
  "max_outputs_per_request": 4
}
```

注意：某些参考图模式存在更严格时长限制；4K 是否可用必须以真实账号和当前 API 能力为准。

调用流程：

```text
GenerationTask
↓
Celery
↓
GoogleVeo31Adapter
↓
Vertex AI Long Running Operation
↓
operation_id
↓
轮询
↓
视频结果
↓
Storage
↓
Video
```

# 六十、Runway Gen-4.5 Adapter

类名：

```text
RunwayGen45Adapter
```

配置：

```text
provider = runway
adapter_type = runway_gen45
model_id = gen4.5
api_base_url
api_key
api_version
```

建议 capabilities：

```json
{
  "text_to_video": true,
  "image_to_video": true,
  "supports_first_frame": true,
  "supports_reference_image": true,
  "duration_mode": "range",
  "duration_min": 2,
  "duration_max": 10,
  "resolutions": ["720p"],
  "aspect_ratios_text_to_video": ["16:9", "9:16"],
  "aspect_ratios_image_to_video": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
  "fps": [24, 25],
  "max_images": 1
}
```

必须按 `generation_type` 分别校验 T2V / I2V 支持比例。

# 六十一、Seedance 2.5 Adapter

第一阶段建议通过 Runway Developer API 接入：

```text
RunwaySeedance25Adapter
```

配置：

```text
provider = runway
adapter_type = runway_seedance25
model_id = seedance2_5
api_base_url
api_key
api_version
```

建议 capabilities：

```json
{
  "text_to_video": true,
  "image_to_video": true,
  "supports_first_frame": true,
  "supports_last_frame": true,
  "supports_reference_image": true,
  "supports_reference_video": true,
  "supports_reference_audio": true,
  "native_audio": true,
  "duration_mode": "range",
  "duration_min": 4,
  "duration_max": 30,
  "resolutions": ["480p", "720p", "1080p"],
  "aspect_ratios": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
  "max_images": 30,
  "max_reference_videos": 10,
  "max_reference_audios": 10
}
```

不同 Provider 对 Seedance 暴露的参数可能不同，因此只允许使用当前 Provider 实际支持的字段。

# 六十二、Luma Ray 3.2 Adapter

类名：

```text
LumaRay32Adapter
```

配置：

```text
provider = luma
adapter_type = luma_ray32
model_id = ray-3.2
api_base_url
api_key
```

建议 capabilities：

```json
{
  "text_to_video": true,
  "image_to_video": true,
  "supports_first_frame": true,
  "supports_last_frame": true,
  "supports_reference_image": true,
  "supports_loop": true,
  "supports_hdr": true,
  "duration_mode": "enum",
  "durations": [5, 10],
  "resolutions": ["360p", "540p", "720p", "1080p"],
  "aspect_ratios": ["9:16", "3:4", "1:1", "4:3", "16:9", "21:9"]
}
```

第一阶段可以不在 UI 暴露全部 HDR / Loop 高级参数，但数据库和 Adapter 要能扩展。

# 六十三、MiniMax Hailuo 2.3 Adapter

类名：

```text
MiniMaxHailuo23Adapter
```

配置：

```text
provider = minimax
adapter_type = minimax_hailuo23
model_id = MiniMax-Hailuo-2.3
api_base_url
api_key
```

建议 capabilities：

```json
{
  "text_to_video": true,
  "image_to_video": true,
  "supports_first_frame": true,
  "native_audio": false,
  "duration_mode": "enum",
  "durations": [6, 10],
  "resolution_duration_matrix": {
    "768p": [6, 10],
    "1080p": [6]
  },
  "resolutions": ["768p", "1080p"],
  "fps": [24],
  "max_images": 1,
  "max_image_size_mb": 20,
  "supported_image_formats": ["jpg", "jpeg", "png", "webp"],
  "image_aspect_ratio_min": 0.4,
  "image_aspect_ratio_max": 2.5,
  "max_prompt_length": 2000
}
```

后端必须校验分辨率与时长组合。

# 六十四、模型 Adapter Factory

建议：

```python
class VideoModelAdapterFactory:
    mapping = {
        "google_veo31": GoogleVeo31Adapter,
        "runway_gen45": RunwayGen45Adapter,
        "runway_seedance25": RunwaySeedance25Adapter,
        "luma_ray32": LumaRay32Adapter,
        "minimax_hailuo23": MiniMaxHailuo23Adapter,
        "mock_video": MockVideoModelAdapter,
    }
```

禁止在 Service 内大量 `if provider == ...`。


模型配置管理员 API 必须拆分：

```text
GET/POST/PATCH/DELETE /api/v1/admin/model-providers
GET/POST/PATCH/DELETE /api/v1/admin/model-accounts
GET/POST/PATCH/DELETE /api/v1/admin/video-models

POST /api/v1/admin/model-accounts/{id}/test
POST /api/v1/admin/video-models/{id}/test
```

普通用户只允许：

```text
GET /api/v1/video-models
```

并且只能取得已启用模型及安全字段。

# 六十五、真实模型配置与 Seed

开发环境只默认启用：

```text
Mock Video Model
```

可以 Seed 5 个真实模型模板，但：

```text
enabled = false
```

管理员填入真实凭证并测试连接后再启用。

建议增加：

```text
POST /api/v1/admin/video-models/{id}/test
```

用于验证 Endpoint、Model ID、Project/Region、认证配置。

# 六十六、第一阶段发布平台固定范围

正式公开发布平台固定为：

```text
X
Instagram
YouTube
Facebook
```

取消 WhatsApp。

这四个平台统一定位为“公开内容发布平台”，但具体内容能力仍由各自 `capabilities JSONB` 决定。

# 六十七、模型侧与发布侧的分层原则

两侧结构应保持一致的设计思想：

```text
模型侧：
ModelProvider
    ↓
ModelAccount
    ↓
VideoModel

发布侧：
PublishPlatform
    ↓
PublishAccount
```

模型 Provider/Account 与发布 Platform/Account 都必须分离配置。

# 六十七、Platform 与 Account 严格分离

必须保持：

```text
PublishPlatform
    ↓
PublishAccount
```

示例：

```text
YouTube
├── 公司官方频道
└── 产品频道

Instagram
├── Japan Official
└── Global Official

X
└── Company Official

Facebook
├── Company Page
└── Product Page
```

平台层保存：

```text
API Base URL
API Version
认证类型
Adapter 类型
Capabilities
平台级配置
```

账号层保存：

```text
外部账号 ID
Page ID / Channel ID / IG User ID
Access Token
Refresh Token
Token Expire
Scopes
账号状态
```

# 六十八、publish_platforms 表增强

建议字段：

```text
id
name
code
adapter_type
api_base_url
api_version
auth_type
capabilities JSONB
extra_config JSONB
enabled
created_at
updated_at
```

`code`：

```text
x
instagram
youtube
facebook
mock
```

# 六十九、publish_accounts 表增强

建议字段：

```text
id
platform_id
name
account_identifier
external_account_id
page_id
channel_id
ig_user_id
client_id
client_secret
access_token
refresh_token
token_expires_at
authorized_scopes JSONB
extra_config JSONB
enabled
created_at
updated_at
```

不要求每个平台都使用所有字段。

# 七十、统一发布平台 capabilities

建议：

```json
{
  "public_publish": true,
  "supports_text": true,
  "supports_image": false,
  "supports_video": true,
  "supports_reel": false,
  "supports_story": false,
  "supports_carousel": false,
  "supports_title": false,
  "supports_description": true,
  "supports_tags": false,
  "supports_privacy": false,
  "supports_schedule": false,
  "requires_public_media_url": false,
  "requires_oauth": true,
  "extra": {}
}
```

前端发布表单必须基于该 JSON 动态显示字段。

# 七十一、X Publish Adapter

类名：

```text
XPublishAdapter
```

平台配置：

```text
code = x
adapter_type = x_v2
api_base_url = https://api.x.com
auth_type = oauth2_pkce
```

建议 scopes：

```text
tweet.read
tweet.write
users.read
media.write
offline.access
```

账号保存：

```text
external_account_id
access_token
refresh_token
token_expires_at
authorized_scopes
```

建议 capabilities：

```json
{
  "public_publish": true,
  "supports_text": true,
  "supports_image": true,
  "supports_video": true,
  "supports_title": false,
  "supports_description": false,
  "supports_tags": false,
  "requires_public_media_url": false,
  "requires_oauth": true
}
```

流程：

```text
Video
↓
Media Upload
↓
media_id
↓
POST /2/tweets
↓
Post ID / URL
```

# 七十二、Instagram Publish Adapter

类名：

```text
InstagramPublishAdapter
```

只支持符合 Meta API 要求的 Instagram Professional Account。

第一阶段重点：

```text
Reel
普通视频
```

后续扩展：

```text
Story
Carousel
```

配置：

```text
code = instagram
adapter_type = instagram_graph
api_base_url = https://graph.instagram.com
api_version = 当前支持版本
auth_type = oauth2
```

账号：

```text
ig_user_id
access_token
token_expires_at
authorized_scopes
```

如果使用 Instagram Login，至少考虑：

```text
instagram_business_basic
instagram_business_content_publish
```

建议 capabilities：

```json
{
  "public_publish": true,
  "supports_image": true,
  "supports_video": true,
  "supports_reel": true,
  "supports_story": true,
  "supports_carousel": true,
  "supports_caption": true,
  "requires_public_media_url": true,
  "requires_oauth": true
}
```

Instagram 发布时媒体必须能被 Meta 从公网 URL 拉取。

流程：

```text
Video
↓
公网 URL
↓
Create Media Container
↓
container_id
↓
轮询处理状态
↓
FINISHED
↓
media_publish
↓
IG Media ID / URL
```

# 七十三、YouTube Publish Adapter

类名：

```text
YouTubePublishAdapter
```

平台配置：

```text
code = youtube
adapter_type = youtube_data_api_v3
api_base_url = https://www.googleapis.com/youtube/v3
upload_base_url = https://www.googleapis.com/upload/youtube/v3
auth_type = oauth2
```

至少需要：

```text
Google Cloud Project
YouTube Data API v3
OAuth Client ID
OAuth Client Secret
Redirect URI
```

核心 scope：

```text
https://www.googleapis.com/auth/youtube.upload
```

账号：

```text
channel_id
access_token
refresh_token
token_expires_at
authorized_scopes
```

建议 capabilities：

```json
{
  "public_publish": true,
  "supports_video": true,
  "supports_title": true,
  "supports_description": true,
  "supports_tags": true,
  "supports_privacy": true,
  "supports_schedule": true,
  "supports_thumbnail": true,
  "supports_made_for_kids": true,
  "supports_synthetic_media_disclosure": true,
  "requires_public_media_url": false,
  "requires_oauth": true
}
```

发布字段至少支持：

```text
title
description
tags
category_id
privacy_status
publish_at
self_declared_made_for_kids
contains_synthetic_media
```

由于系统主要生成 AI 视频，必须保留 `contains_synthetic_media`。

流程：

```text
Storage Video
↓
Resumable Upload
↓
videos.insert
↓
video_id
↓
处理完成
↓
YouTube URL
```

# 七十四、Facebook Publish Adapter

类名：

```text
FacebookPublishAdapter
```

第一阶段按 Facebook Page 发布设计。

不要默认支持个人 Profile 自动发布。

重点支持：

```text
Page Video
Page Reel
```

可扩展：

```text
Text Post
Image Post
```

配置：

```text
code = facebook
adapter_type = facebook_graph
api_base_url = https://graph.facebook.com
api_version = 当前支持版本
auth_type = oauth2
```

账号：

```text
page_id
access_token
client_id
client_secret
token_expires_at
authorized_scopes
```

至少考虑 Page 发布相关权限：

```text
pages_show_list
pages_manage_posts
pages_read_engagement
```

建议 capabilities：

```json
{
  "public_publish": true,
  "supports_text": true,
  "supports_image": true,
  "supports_video": true,
  "supports_reel": true,
  "supports_title": true,
  "supports_description": true,
  "supports_schedule": true,
  "requires_public_media_url": false,
  "requires_oauth": true,
  "extra": {
    "reel": {
      "aspect_ratios": ["9:16"],
      "duration_min": 4,
      "duration_max": 60,
      "min_resolution": "540x960"
    }
  }
}
```

Reel 流程：

```text
Create Upload Session
↓
上传视频
↓
Finish Upload Phase
↓
PUBLISHED / SCHEDULED
↓
video_id / URL
```

# 七十五、Publish Adapter Factory

建议：

```python
class PublishAdapterFactory:
    mapping = {
        "x_v2": XPublishAdapter,
        "instagram_graph": InstagramPublishAdapter,
        "youtube_data_api_v3": YouTubePublishAdapter,
        "facebook_graph": FacebookPublishAdapter,
        "mock_publish": MockPublishAdapter,
    }
```

业务 Service 只能依赖统一 `PublishPlatformAdapter`。

# 七十六、OAuth 账号连接

真实系统优先做“连接账号”，不要要求管理员长期手工复制 Token。

建议 API：

```text
GET  /api/v1/admin/platforms/{platform_id}/oauth/start
GET  /api/v1/admin/platforms/{platform_id}/oauth/callback
POST /api/v1/admin/accounts/{account_id}/refresh
POST /api/v1/admin/accounts/{account_id}/test
```

流程：

```text
管理员点击连接账号
↓
官方 OAuth
↓
授权
↓
Callback
↓
交换 Token
↓
获取外部账号信息
↓
保存 PublishAccount
```

# 七十七、统一发布请求

建议：

```json
{
  "video_id": "uuid",
  "common": {
    "title": "公共标题",
    "content": "公共正文",
    "description": "公共描述",
    "tags": ["AI", "Video"]
  },
  "targets": [
    {
      "platform_id": "uuid",
      "account_id": "uuid",
      "publish_type": "video",
      "overrides": {}
    }
  ]
}
```

`publish_type` 根据平台 capabilities 可为：

```text
video
reel
post
```

# 七十八、publish_tasks 表增强

建议追加：

```text
publish_type
common_payload JSONB
platform_payload JSONB
provider_upload_id
provider_container_id
```

完整建议：

```text
id
video_id
user_id
platform_id
account_id
publish_type
status
title
content
description
tags
common_payload JSONB
platform_payload JSONB
provider_upload_id
provider_container_id
platform_post_id
platform_post_url
idempotency_key
error_code
error_message
retry_count
created_at
started_at
completed_at
updated_at
```

# 七十九、发布字段映射

系统统一字段：

```text
title
content
description
tags
publish_type
```

Adapter 映射：

```text
X:
content -> Post text

Instagram:
content / description -> caption

YouTube:
title / description / tags -> snippet

Facebook:
title / description -> Page Video / Reel 参数
```

禁止前端直接提交完整第三方 API 原始 Body。

# 八十、真实 Adapter 目录结构

最终建议：

```text
adapters/
├── video_models/
│   ├── base.py
│   ├── factory.py
│   ├── mock.py
│   ├── google_veo31.py
│   ├── runway_gen45.py
│   ├── runway_seedance25.py
│   ├── luma_ray32.py
│   └── minimax_hailuo23.py
│
└── publishing/
    ├── base.py
    ├── factory.py
    ├── mock.py
    ├── x.py
    ├── instagram.py
    ├── youtube.py
    └── facebook.py
```

# 八十一、更新后的验收要求

## 视频模型

- [ ] Veo 3.1 Adapter 可加载
- [ ] Gen-4.5 Adapter 可加载
- [ ] Seedance 2.5 Adapter 可加载
- [ ] Ray 3.2 Adapter 可加载
- [ ] Hailuo 2.3 Adapter 可加载
- [ ] 无 Key 时服务仍能启动
- [ ] capabilities 校验正常
- [ ] Secret 不泄露

## 发布平台

- [ ] X Adapter
- [ ] Instagram Adapter
- [ ] YouTube Adapter
- [ ] Facebook Adapter
- [ ] Platform / Account 分离
- [ ] 一个 target 一个 PublishTask
- [ ] OAuth 配置结构存在
- [ ] Token 过期有处理策略
- [ ] 多平台互不影响
- [ ] 失败只重试对应任务
- [ ] Secret 不泄露

# 八十二、真实第三方验证边界

如果当前缺少真实凭证，必须完成：

```text
Adapter 代码结构
数据库配置结构
参数校验
OAuth / Token 结构
Mock 测试
README 接入步骤
```

但最终报告必须明确：

```text
尚未完成真实第三方平台端到端验证
```

禁止把 Mock 成功结果描述成真实 API 已成功。


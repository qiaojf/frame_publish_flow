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

# 十、video_models

表示管理员配置的 AI 视频模型。

字段至少：

```text
id
name
code
provider
adapter_type

api_base_url
api_key_encrypted_or_secret
model_id

supports_text_to_video
supports_image_to_video

capabilities JSONB
extra_config JSONB

enabled

created_at
updated_at
```

其中：

`capabilities` 示例：

```json
{
  "durations": [5, 10],
  "aspect_ratios": ["16:9", "9:16"],
  "resolutions": ["720p", "1080p"],
  "max_images": 1
}
```

要求：

- code 唯一
- enabled 建索引
- API Key 不能通过普通查询返回完整值
- 日志禁止输出完整 Secret

---

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
WhatsApp
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
Mock Video Model
```

支持：

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
WhatsAppAdapter
MockPublishAdapter
```

真实平台实现前必须查对应平台当前官方 API。

禁止伪造不存在的接口能力。

---

# 三十二、WhatsApp 特别处理

不要假设 WhatsApp 一定支持和 YouTube/X 完全一样的“公开视频发布”。

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
WhatsApp
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

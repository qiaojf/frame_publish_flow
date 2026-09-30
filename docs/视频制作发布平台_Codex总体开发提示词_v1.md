# 视频制作发布平台——Codex 总体开发提示词

## 一、你的角色

你是一名高级全栈架构师和开发工程师，需要独立完成一个“AI 视频制作 + 多平台发布”的企业内部 Web 平台。

你需要具备以下能力：

- Vue 3 + TypeScript 企业后台开发
- Python + FastAPI 后端开发
- PostgreSQL 数据库设计
- Redis + Celery 异步任务处理
- AI / 视频生成 API 集成
- OAuth2 / 第三方平台 API 集成
- 视频文件管理
- FFmpeg 基础处理
- REST API 设计
- 权限控制
- Docker Compose 本地部署
- 自动化测试
- 企业级日志及异常处理

本项目优先保证：

1. 架构清晰
2. 功能闭环
3. 易于增加新的 AI 视频模型
4. 易于增加新的发布平台
5. 前后端完全解耦
6. 本地能够完整运行
7. 后续容易扩展到生产环境

不要为了追求复杂架构而过度设计。

---

# 二、项目名称

暂定：

**AI 视频制作发布平台**

英文内部项目名可使用：

`video-publish-platform`

---

# 三、项目核心目标

建设一个企业内部使用的视频制作及多平台发布系统。

系统主要完成两个业务闭环：

```text
AI 视频制作
↓
视频资产保存
↓
视频预览
↓
选择发布平台
↓
多平台发布
↓
发布结果追踪
```

系统包含：

1. 视频制作
2. 视频管理
3. 视频发布
4. 大模型配置
5. 发布平台配置
6. 用户管理
7. 操作日志

---

# 四、固定技术栈

除非存在明确技术障碍，否则不要自行更换以下技术栈。

## 4.1 前端

```text
Vue 3
TypeScript
Vite
Element Plus
Pinia
Vue Router
Axios
```

要求：

- 使用 Composition API
- 使用 `<script setup lang="ts">`
- 开启 TypeScript 严格模式
- API 请求统一封装
- 状态管理使用 Pinia
- UI 使用 Element Plus
- 不额外引入大型 UI 框架

---

## 4.2 后端

```text
Python
FastAPI
SQLAlchemy
Alembic
Pydantic
```

要求：

- 使用 REST API
- 前后端完全分离
- ORM 使用 SQLAlchemy
- 数据库迁移使用 Alembic
- 参数校验使用 Pydantic
- API 自动生成 OpenAPI / Swagger 文档

---

## 4.3 数据库

使用：

```text
PostgreSQL 17
```

禁止：

- SQLite 作为正式开发数据库
- MongoDB 替代 PostgreSQL

测试中可以根据需要使用独立测试数据库。

---

## 4.4 异步任务

使用：

```text
Redis
Celery
```

主要处理：

- AI 视频生成
- 视频生成状态轮询
- 视频文件下载
- 缩略图生成
- 多平台视频发布
- 发布状态处理
- 失败任务重试

视频生成和发布任务禁止使用长时间阻塞的 HTTP 请求完成。

---

## 4.5 文件存储

开发阶段支持：

```text
本地文件存储
```

同时预留：

```text
MinIO / S3 Compatible Storage
```

抽象出统一 Storage 接口。

禁止将：

- 视频二进制
- 图片二进制
- 大文件

直接保存到 PostgreSQL。

PostgreSQL 只保存：

- 文件 URL
- 文件路径
- 文件大小
- MIME Type
- 元数据

---

## 4.6 视频处理

使用：

```text
FFmpeg
```

主要用于：

- 获取视频元数据
- 视频缩略图生成
- 必要的视频格式检测

第一期不开发在线视频剪辑。

---

## 4.7 用户认证

使用：

```text
JWT
```

至少支持：

- 登录
- Token 验证
- 当前用户获取
- 权限控制
- Token 过期处理

密码必须 Hash 保存。

禁止明文保存密码。

---

# 五、系统角色

只设计两个角色。

## 5.1 普通用户

权限：

- 登录
- 视频制作
- 文生视频
- 图生视频
- 选择 AI 视频模型
- 查看生成任务
- 查看自己的视频
- 视频预览
- 视频下载
- 删除自己的视频
- 发布自己的视频
- 多平台发布
- 查看自己的发布记录
- 对失败任务重新发布

普通用户不能访问：

- 用户管理
- 模型管理
- 发布平台系统配置
- 系统日志管理

---

# 六、管理员

管理员拥有普通用户全部权限。

另外拥有：

- 用户管理
- 大模型管理
- 发布平台管理
- 发布账号管理
- 系统日志查看

---

# 七、视频制作核心逻辑

不要要求用户手工选择：

- 文生视频
- 图生视频

系统根据输入自动判断。

---

## 7.1 文生视频

当前端提交：

```text
prompt != 空
image == 空
```

则：

```text
generation_type = text_to_video
```

后端调用用户选择模型对应的：

```text
Text To Video
```

接口。

---

## 7.2 图生视频

当前端提交：

```text
prompt != 空
image != 空
```

则：

```text
generation_type = image_to_video
```

后端调用对应模型的：

```text
Image To Video
```

接口。

---

## 7.3 图片上传

第一阶段：

至少支持单张参考图片。

代码结构需要为未来支持多张图片保留扩展能力。

支持常见格式：

```text
jpg
jpeg
png
webp
```

需要限制：

- 文件类型
- 文件大小

限制值通过配置管理，不要写死在业务代码中。

---

# 八、视频生成页面

页面提供以下输入：

## 必填

- Prompt / 视频描述
- 视频生成模型

## 可选

- 参考图片
- 视频比例
- 视频时长
- 视频分辨率

根据模型能力动态展示参数。

例如：

模型 A 支持：

```text
16:9
9:16
5 秒
10 秒
720p
1080p
```

模型 B 只支持：

```text
16:9
5 秒
720p
```

前端必须根据后端返回的：

```text
model capabilities
```

动态生成可选项。

禁止在前端把各厂商参数全部写死。

---

# 九、视频生成模型管理

管理员可以配置多个视频生成模型。

例如：

```text
模型 A
模型 B
模型 C
...
```

第一版不强制绑定具体厂商。

核心目标是先建立统一模型适配器。

---

# 十、模型数据库信息

每个模型至少包含：

```text
id

name
code
provider

api_base_url
api_key
model_id

supports_text_to_video
supports_image_to_video

capabilities

extra_config

enabled

created_at
updated_at
```

其中：

`capabilities`

推荐 PostgreSQL JSONB。

例如：

```json
{
  "durations": [5, 10],
  "aspect_ratios": ["16:9", "9:16"],
  "resolutions": ["720p", "1080p"],
  "max_images": 1
}
```

`extra_config`

也可以使用 JSONB。

用于保存不同厂商特有参数。

---

# 十一、API Key 安全

API Key、Client Secret、Access Token 等敏感信息：

禁止：

- 返回给普通用户
- 前端直接保存
- 日志输出完整 Secret
- API Response 返回完整 Secret

管理员编辑配置时：

列表页面只显示脱敏值。

例如：

```text
sk-****7xA2
```

后端实际调用时读取完整配置。

代码必须为未来使用环境变量或 Secrets Manager 预留能力。

---

# 十二、模型适配层

这是本项目最重要的架构之一。

禁止在业务代码中直接编写：

```python
if model == "xxx":
    ...
elif model == "yyy":
    ...
elif model == "zzz":
    ...
```

应设计：

```text
VideoModelAdapter
```

统一接口。

例如：

```python
class VideoModelAdapter:

    async def create_text_to_video(...):
        pass

    async def create_image_to_video(...):
        pass

    async def get_task_status(...):
        pass

    async def get_result(...):
        pass
```

不同模型分别实现：

```text
ProviderAAdapter
ProviderBAdapter
ProviderCAdapter
```

通过：

```text
ModelAdapterFactory
```

根据数据库模型配置加载对应 Adapter。

以后增加新模型时：

只需要增加：

```text
新的 Adapter
+
模型配置
```

而不需要修改视频生成主流程。

---

# 十三、模拟模型

为了保证项目在没有真实大模型 API Key 的情况下也可以运行：

必须实现：

```text
MockVideoModelAdapter
```

Mock 模型需要模拟：

```text
提交任务
↓
生成中
↓
生成完成
```

方便：

- 本地开发
- 联调
- 自动化测试
- UI 演示

开发环境初始化数据库时：

自动创建一个：

```text
Mock Video Model
```

默认启用。

---

# 十四、视频生成任务

每次点击生成视频：

创建：

```text
video_generation_task
```

---

## 状态

至少：

```text
pending
processing
success
failed
```

建议预留：

```text
cancelled
timeout
```

---

## 保存字段

至少包含：

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

created_at
started_at
completed_at
```

---

# 十五、异步生成流程

完整流程：

```text
前端
↓
POST 创建视频生成任务
↓
FastAPI
↓
写入 PostgreSQL
status = pending
↓
发送 Celery Task
↓
Redis
↓
Celery Worker
↓
调用 VideoModelAdapter
↓
第三方 AI 视频 API
↓
获得 provider_task_id
↓
轮询状态
↓
生成完成
↓
下载视频
↓
Storage 保存
↓
FFmpeg 获取视频信息
↓
生成缩略图
↓
写入 Videos
↓
更新任务
status = success
↓
前端看到结果
```

---

# 十六、前端任务状态获取

第一阶段优先采用：

```text
HTTP Polling
```

例如：

每 3～5 秒查询一次任务状态。

必须封装统一任务查询逻辑。

代码为未来切换：

```text
WebSocket / SSE
```

保留扩展空间。

第一阶段不要为了实时状态强行增加复杂 WebSocket 架构。

---

# 十七、视频资产

视频生成成功后：

必须形成独立：

```text
Video
```

记录。

视频和生成任务不要设计成完全相同的表。

一个生成任务成功后：

```text
GenerationTask
    ↓
Video
```

---

# 十八、Video 数据结构

至少包含：

```text
id
owner_id

generation_task_id

title
description

video_url
thumbnail_url

file_size

duration
width
height

mime_type

created_at
updated_at
```

以后即使视频不来自 AI，也可以加入 Video 表。

---

# 十九、我的视频

普通用户只能看到：

```text
自己创建的视频
```

管理员可以根据需要查看全部。

页面采用卡片或列表形式。

至少显示：

- 缩略图
- 标题
- 生成方式
- 模型
- 时长
- 创建时间
- 当前发布状态

操作：

```text
播放
详情
下载
发布
重新生成
删除
```

删除需要二次确认。

---

# 二十、视频详情页

显示：

- 视频播放器
- 标题
- Prompt
- 参考图片
- 生成模型
- 生成类型
- 视频参数
- 创建时间
- 视频文件信息
- 发布历史

提供：

```text
发布视频
下载视频
重新生成
```

---

# 二十一、视频发布

生成成功的视频可以发布到：

第一阶段平台抽象至少考虑：

```text
X
Instagram
YouTube
WhatsApp
其他 SNS / 社交平台
```

注意：

不同平台实际支持的视频发布方式、账号类型、OAuth 权限、审核要求、媒体上传机制可能不同。

实际实现任何真实平台接口前：

必须参考该平台当前官方 API 文档。

禁止凭经验硬编码不存在的接口。

如果某个平台当前官方 API 无法支持预期的“公开发布视频”能力：

应：

1. 保留该平台 Adapter
2. 明确标记能力限制
3. 不伪造发布成功结果
4. 在 README 中记录限制

---

# 二十二、多平台选择

发布页面支持：

```text
Checkbox 多选
```

例如：

```text
☑ X
☑ Instagram
☑ YouTube
☐ WhatsApp
```

用户可以一次选择多个平台。

---

# 二十三、一个平台一个发布任务

这是强制设计。

错误方式：

```text
一个视频
↓
一个 PublishTask
↓
里面保存多个平台
```

正确方式：

```text
Video A
│
├── PublishTask → YouTube
├── PublishTask → Instagram
└── PublishTask → X
```

这样：

```text
YouTube success
Instagram success
X failed
```

互相不会影响。

---

# 二十四、发布内容

统一发布表单提供：

- 标题
- 正文
- Description
- Tags / Hashtags
- 封面

具体平台需要哪些字段：

由：

```text
Platform Capabilities
```

决定。

例如：

YouTube：

```text
title
description
tags
```

Instagram：

```text
caption
```

X：

```text
text
```

前端根据平台能力动态显示字段。

---

# 二十五、不同平台内容差异

第一阶段允许：

先填写一份：

```text
公共发布内容
```

再允许用户：

针对某个平台进行覆盖。

例如：

```text
公共标题
公共描述

↓

YouTube：
使用公共内容

Instagram：
覆盖 Caption

X：
覆盖发布文字
```

数据结构需要支持这一点。

---

# 二十六、发布平台管理

管理员可以管理平台：

```text
X
Instagram
YouTube
WhatsApp
...
```

平台字段至少包含：

```text
id

name
code

adapter_type

api_base_url

capabilities

enabled

created_at
updated_at
```

---

# 二十七、发布平台和发布账号必须分开

不要把：

```text
YouTube
```

和：

```text
公司官方 YouTube 账号
```

当成一条记录。

应设计：

```text
PublishPlatform
    ↓
PublishAccount
```

例如：

```text
YouTube
│
├── 公司官方频道
├── 产品频道
└── 日本分公司频道
```

---

# 二十八、发布账号

字段至少包括：

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

extra_config

enabled

created_at
updated_at
```

敏感字段必须脱敏。

---

# 二十九、发布 Adapter

建立统一：

```text
PublishPlatformAdapter
```

建议接口：

```python
class PublishPlatformAdapter:

    async def publish_video(...):
        pass

    async def get_publish_status(...):
        pass

    async def refresh_token(...):
        pass
```

实现形式：

```text
YouTubeAdapter
XAdapter
InstagramAdapter
WhatsAppAdapter
MockPublishAdapter
```

使用：

```text
PublishAdapterFactory
```

创建具体 Adapter。

业务层禁止直接依赖 YouTube/X 等平台 SDK。

---

# 三十、Mock 发布平台

必须实现：

```text
MockPublishAdapter
```

本地开发时：

可以模拟：

```text
发布成功
发布失败
处理中
```

这样没有第三方平台账号时：

仍然能够完整验证：

```text
生成视频
↓
发布
↓
查看发布结果
```

整个业务闭环。

---

# 三十一、发布任务状态

至少：

```text
pending
publishing
success
failed
```

预留：

```text
cancelled
```

保存：

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

platform_post_id
platform_post_url

error_code
error_message

created_at
started_at
completed_at
```

---

# 三十二、失败重新发布

如果：

```text
YouTube success
Instagram success
X failed
```

用户点击重新发布：

只重新执行：

```text
X
```

禁止重复发布：

```text
YouTube
Instagram
```

---

# 三十三、发布记录页面

显示：

- 视频缩略图
- 视频名称
- 发布平台
- 发布账号
- 发布状态
- 发布时间
- 发布 URL
- 错误信息

支持筛选：

```text
平台
状态
时间
关键词
```

失败任务提供：

```text
重新发布
```

成功任务存在 URL 时：

提供：

```text
查看发布内容
```

---

# 三十四、用户管理

管理员页面支持：

```text
新增用户
修改用户
启用
禁用
删除
修改角色
重置密码
```

字段至少：

```text
username
display_name
email
password_hash
role
enabled
created_at
updated_at
last_login_at
```

角色：

```text
admin
user
```

---

# 三十五、权限设计

后端必须实际进行权限判断。

禁止仅依靠：

```text
前端隐藏菜单
```

普通用户请求管理员 API：

必须返回：

```text
403 Forbidden
```

同时用户不能：

- 查看别人的私有视频
- 删除别人的视频
- 发布别人的视频
- 查看别人的敏感任务信息

管理员除外。

---

# 三十六、日志

建立：

```text
AuditLog
```

至少记录：

```text
用户登录
创建视频任务
视频生成成功
视频生成失败
删除视频
创建发布任务
发布成功
发布失败
重新发布
新增用户
修改用户
修改模型配置
修改平台配置
修改账号配置
```

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

管理员可以查看。

禁止日志记录完整：

```text
API Key
Access Token
Refresh Token
密码
```

---

# 三十七、前端页面

至少实现以下页面。

## 公共

```text
/login
```

---

## 普通用户

```text
/dashboard

/video/create

/videos

/videos/:id

/publish

/publish/history
```

---

## 管理员

```text
/admin/users

/admin/models

/admin/models/:id

/admin/platforms

/admin/platforms/:id

/admin/accounts

/admin/logs
```

---

# 三十八、后台菜单

建议：

```text
首页

视频制作

视频管理
  └─ 我的视频

发布管理
  ├─ 发布视频
  └─ 发布记录

系统管理
  ├─ 用户管理
  ├─ 大模型管理
  ├─ 发布平台管理
  ├─ 发布账号管理
  └─ 操作日志
```

普通用户不显示：

```text
系统管理
```

---

# 三十九、首页 Dashboard

显示简单统计即可。

普通用户：

```text
我的视频数量
今日生成任务
生成中
发布成功
发布失败

最近生成视频
最近发布记录
```

管理员可以增加：

```text
总用户数
视频总数
任务总量
```

第一版不要做复杂 BI。

---

# 四十、前端 API 架构

建议：

```text
src/api/

auth.ts
users.ts
models.ts
videos.ts
generation.ts
platforms.ts
publish.ts
logs.ts
```

统一 Axios 实例：

```text
src/utils/request.ts
```

实现：

- Base URL
- JWT 自动附加
- 401 统一处理
- 错误统一处理
- 超时处理

---

# 四十一、前端类型定义

禁止大量使用：

```typescript
any
```

建立：

```text
src/types/
```

至少：

```text
user.ts
video.ts
generation.ts
model.ts
platform.ts
publish.ts
common.ts
```

前后端字段命名需要保持统一。

---

# 四十二、后端模块结构

推荐：

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── models.py
│   │   ├── videos.py
│   │   ├── generation.py
│   │   ├── platforms.py
│   │   ├── publish.py
│   │   └── logs.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── permissions.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   │
│   ├── models/
│   │
│   ├── schemas/
│   │
│   ├── services/
│   │   ├── video_generation_service.py
│   │   ├── video_service.py
│   │   ├── publishing_service.py
│   │   └── storage_service.py
│   │
│   ├── adapters/
│   │   ├── video_models/
│   │   └── publishing/
│   │
│   ├── tasks/
│   │   ├── generation_tasks.py
│   │   └── publish_tasks.py
│   │
│   └── utils/
│
├── alembic/
├── tests/
├── requirements.txt
└── alembic.ini
```

允许根据最佳实践小幅调整。

但必须保持：

```text
API
Service
Adapter
Model
Schema
Task
```

职责分离。

---

# 四十三、前端目录

建议：

```text
frontend/
│
├── src/
│   ├── api/
│   ├── assets/
│   ├── components/
│   ├── layouts/
│   ├── router/
│   ├── stores/
│   ├── types/
│   ├── utils/
│   └── views/
│
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

# 四十四、数据库核心表

至少设计：

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

根据必要性可以增加：

```text
refresh_tokens
uploaded_assets
```

不要为了理论上的未来需求建立大量无用表。

---

# 四十五、数据库约束

必须：

- Primary Key
- Foreign Key
- 必要索引
- created_at
- updated_at

重要字段：

添加索引。

例如：

```text
user_id
status
model_id
video_id
platform_id
created_at
```

外键删除策略需要明确。

不要随意 Cascade 删除重要历史记录。

---

# 四十六、API 设计

API 前缀统一：

```text
/api/v1
```

例如：

```text
POST   /api/v1/auth/login
GET    /api/v1/auth/me

GET    /api/v1/video-models
POST   /api/v1/admin/video-models

POST   /api/v1/generation/tasks
GET    /api/v1/generation/tasks/{id}

GET    /api/v1/videos
GET    /api/v1/videos/{id}
DELETE /api/v1/videos/{id}

GET    /api/v1/publish/platforms
POST   /api/v1/publish/tasks
GET    /api/v1/publish/tasks

GET    /api/v1/admin/users
GET    /api/v1/admin/logs
```

具体路径可以合理优化。

---

# 四十七、统一返回结构

建议成功：

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

不要让不同模块使用完全不同的返回风格。

---

# 四十八、异常处理

必须统一异常处理。

例如：

```text
400 参数错误
401 未登录
403 无权限
404 资源不存在
409 状态冲突
422 数据校验错误
500 系统错误
```

第三方 API 错误不要直接将原始 Stack Trace 返回前端。

需要转换为：

用户可以理解的错误信息。

完整错误写服务端日志。

---

# 四十九、任务幂等性

视频发布尤其要注意重复点击。

前端：

提交按钮在请求过程中禁用。

后端：

需要避免因为：

```text
双击
网络重试
Celery 重试
```

导致同一任务重复发布。

为发布任务设计基本幂等机制。

---

# 五十、任务重试

对：

```text
网络超时
临时性 5xx
平台暂时不可用
```

允许有限次数自动重试。

但对于：

```text
401
权限不足
参数错误
内容违反平台要求
```

不要无限重试。

最大重试次数必须可以配置。

---

# 五十一、配置文件

使用：

```text
.env
```

提供：

```text
.env.example
```

至少包含：

```text
DATABASE_URL
REDIS_URL

JWT_SECRET_KEY

STORAGE_TYPE
STORAGE_PATH

UPLOAD_MAX_SIZE

CELERY_BROKER_URL

CORS_ORIGINS
```

不要提交真实密码和 API Key。

---

# 五十二、本地开发

提供：

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

前端和后端可以：

- Docker 运行

或者：

- 本机开发模式运行

必须在 README 中说明。

---

# 五十三、初始化数据库

提供：

```text
seed
```

开发初始化数据至少：

## 管理员

```text
admin
```

默认密码只能用于开发环境。

README 明确要求首次使用后修改。

---

## 模型

```text
Mock Video Model
```

支持：

```text
文生视频
图生视频
```

---

## 发布平台

```text
Mock Platform
```

方便完整测试。

---

# 五十四、UI 要求

整体风格：

```text
简洁
现代
企业内部管理系统
```

不需要：

- 炫酷动画
- 大量渐变
- 复杂视觉效果

重点：

- 操作直观
- 状态清晰
- 错误清晰
- 表单简单
- 视频预览方便

---

# 五十五、状态视觉

不同状态使用：

```text
Tag
Badge
Progress
```

例如：

```text
等待
处理中
成功
失败
```

生成中可以显示：

```text
进度条
```

如果模型没有真实 progress：

使用：

```text
处理中
```

禁止伪造百分比。

---

# 五十六、第一阶段不做

不要实现以下功能：

```text
在线视频剪辑
复杂时间轴
AI 数字人
AI 配音
自动字幕
自动生成脚本
自动 Prompt 优化
视频模板市场
评论管理
私信管理
粉丝管理
复杂 BI
审批流程
定时发布
移动 APP
微服务
Kubernetes
```

除非完成核心需求后且确实有必要，否则不要自行扩展。

---

# 五十七、测试要求

至少包含：

## 后端

使用：

```text
pytest
```

覆盖：

- 登录
- 权限
- 创建生成任务
- 文生视频判断
- 图生视频判断
- Mock Adapter
- 视频查询
- 视频权限
- 创建发布任务
- 多平台拆分
- 发布失败
- 重新发布
- 管理员接口权限

---

## 前端

至少确保：

```text
npm run build
```

无错误。

关键 TypeScript 不允许存在明显类型错误。

---

# 五十八、必须验证的核心场景

### 场景 1

普通用户：

```text
输入文字
↓
不上传图片
↓
选择 Mock Model
↓
生成
```

结果：

```text
自动识别文生视频
↓
任务成功
↓
生成 Video
```

---

### 场景 2

普通用户：

```text
输入文字
+
上传图片
↓
选择 Mock Model
↓
生成
```

结果：

```text
自动识别图生视频
↓
生成成功
```

---

### 场景 3

用户选择：

```text
平台 A
平台 B
平台 C
```

点击发布。

数据库必须产生：

```text
3 个独立 PublishTask
```

---

### 场景 4

模拟：

```text
A success
B success
C failed
```

用户重新发布 C。

必须：

```text
只重新执行 C
```

---

### 场景 5

普通用户访问：

```text
/admin/*
```

必须：

```text
前端阻止
+
后端返回 403
```

---

### 场景 6

没有配置任何真实第三方 API。

整个系统依靠：

```text
Mock Model
+
Mock Publish Platform
```

仍然可以完成：

```text
登录
↓
制作视频
↓
查看视频
↓
发布
↓
查看发布结果
```

---

# 五十九、验收标准

项目完成必须满足以下条件。

## 登录

- [ ] 管理员可以登录
- [ ] 普通用户可以登录
- [ ] JWT 正常
- [ ] 权限正常

## 视频制作

- [ ] 可以输入 Prompt
- [ ] 可以上传图片
- [ ] 可以选择模型
- [ ] 没图片自动走文生视频
- [ ] 有图片自动走图生视频
- [ ] 创建异步任务
- [ ] 可以查看状态
- [ ] 可以得到生成视频

## 视频管理

- [ ] 视频列表
- [ ] 视频详情
- [ ] 视频播放
- [ ] 视频下载
- [ ] 视频删除

## 发布

- [ ] 可以选择多个平台
- [ ] 一个平台注册一个任务
- [ ] 可以异步发布
- [ ] 可以查看状态
- [ ] 失败可以重新发布
- [ ] 不影响其他成功平台

## 管理

- [ ] 用户管理
- [ ] 模型管理
- [ ] 模型启用 / 禁用
- [ ] 发布平台管理
- [ ] 发布账号管理
- [ ] 操作日志

## 工程

- [ ] PostgreSQL Migration 正常
- [ ] Redis 正常
- [ ] Celery 正常
- [ ] Mock Adapter 正常
- [ ] 前端 build 正常
- [ ] 后端测试正常
- [ ] README 完整

---

# 六十、README 必须包含

README 至少说明：

```text
项目简介

技术栈

项目目录

环境要求

安装方法

.env 配置

PostgreSQL 启动

Redis 启动

数据库 migration

初始化数据

启动 FastAPI

启动 Celery Worker

启动 Vue

默认管理员账号

Mock 模型使用方法

Mock 发布平台使用方法

真实模型 Adapter 扩展方法

真实发布平台 Adapter 扩展方法

运行测试

常见问题
```

---

# 六十一、开发执行顺序

不要无序开发。

严格按照以下顺序推进。

## Phase 1：项目骨架

完成：

```text
frontend
backend
docker-compose
PostgreSQL
Redis
基础配置
```

---

## Phase 2：数据库

完成：

```text
数据库 Model
Alembic Migration
初始化数据
```

---

## Phase 3：登录权限

完成：

```text
登录
JWT
用户
管理员权限
```

先验证权限。

---

## Phase 4：模型管理

完成：

```text
VideoModel
Model Adapter
Mock Adapter
管理员模型配置
```

---

## Phase 5：视频生成

完成：

```text
创建任务
Celery
Text to Video
Image to Video
状态查询
视频保存
```

做到第一个完整闭环。

---

## Phase 6：视频管理

完成：

```text
视频列表
视频详情
播放
下载
删除
```

---

## Phase 7：发布平台

完成：

```text
Platform
Account
Publish Adapter
Mock Publish Adapter
```

---

## Phase 8：视频发布

完成：

```text
多平台选择
多个 PublishTask
Celery 发布
结果记录
失败重试
```

---

## Phase 9：管理员页面

完成：

```text
用户管理
模型管理
平台管理
账号管理
日志
```

---

## Phase 10：测试与联调

完整跑通：

```text
Vue
↓
FastAPI
↓
PostgreSQL
↓
Redis
↓
Celery
↓
Mock Video Model
↓
Video
↓
Mock Publish
```

---

# 六十二、开发过程规则

开发过程中必须遵守：

### 1

不要只生成 Demo 页面。

最终需要：

```text
真实前端
+
真实后端
+
真实数据库
+
真实任务队列
```

能够联调运行。

### 2

不要用前端 Mock 数据冒充后端功能。

### 3

只有：

```text
AI 视频厂商
发布平台
```

允许使用 Adapter Mock。

### 4

每完成一个阶段：

运行对应测试。

### 5

发现 Bug：

直接修复。

不要只写 TODO。

### 6

如果某第三方 API 需要真实账号或凭证：

完成：

```text
Adapter
配置
参数校验
调用代码结构
Mock 实现
```

不要伪造真实发布结果。

### 7

不要因为第三方凭证不存在而阻断整个系统开发。

### 8

API Key 等 Secret 不允许硬编码。

### 9

不要擅自改变已经确定的核心业务逻辑。

---

# 六十三、代码质量要求

要求：

- 命名清楚
- 函数职责单一
- 避免超长文件
- 避免重复代码
- 提供必要注释
- 不要大量无意义注释
- 不要创建没有实际用途的抽象层
- 不要使用大量 `any`
- Python 增加类型标注
- 所有关键异常必须处理

---

# 六十四、最终项目结构目标

```text
video-publish-platform/
│
├── frontend/
│
├── backend/
│
├── storage/
│
├── docker-compose.yml
│
├── .env.example
│
├── README.md
│
└── docs/
```

`docs/` 中至少保存：

```text
architecture.md
database.md
api.md
```

---

# 六十五、最终交付结果

全部开发完成以后：

不要只回答：

```text
完成了
```

必须返回开发报告，包括：

## 1. 已完成模块

逐项说明。

## 2. 项目结构

说明主要目录。

## 3. 数据库

说明：

- 表
- Migration
- Seed

## 4. API

说明主要 API。

## 5. 前端

说明完成页面。

## 6. 异步任务

说明：

- Redis
- Celery
- Task 工作流程

## 7. Adapter

说明：

- Video Model Adapter
- Publish Adapter
- Mock Adapter

## 8. 测试

给出实际执行过的：

```text
pytest
npm run build
```

以及结果。

## 9. 启动方法

给出从空环境启动整个项目的完整命令。

## 10. 默认账号

明确开发环境管理员账号。

## 11. 尚未完成项

如果某些第三方真实 API 因为缺少：

```text
API Key
OAuth Client
平台账号
```

不能实际测试：

必须明确说明。

不要声称已经真实发布成功。

---

# 六十六、最重要的架构原则

整个项目始终遵循以下结构：

```text
                     Vue 3
                       │
                       │ REST API
                       ▼
                    FastAPI
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
   PostgreSQL        Redis        Storage
                       │
                       ▼
                 Celery Worker
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
       Video Adapter       Publish Adapter
             │                   │
       AI 视频模型          社交媒体平台
```

视频生成：

```text
用户
↓
Prompt / Image
↓
选择模型
↓
GenerationTask
↓
Celery
↓
VideoModelAdapter
↓
视频生成
↓
Video
```

视频发布：

```text
Video
↓
选择多个平台
↓
每个平台建立一个 PublishTask
↓
Celery
↓
PublishPlatformAdapter
↓
第三方平台
↓
独立保存发布结果
```

始终保证：

**模型可插拔、平台可插拔、任务异步化、视频资产独立、前后端解耦。**

---

# 六十七、当前第一阶段最终目标

本次开发的目标不是做一个庞大的视频营销 SaaS。

目标是首先稳定完成：

```text
登录
  ↓
输入 Prompt
  ↓
可选上传图片
  ↓
选择 AI 视频模型
  ↓
生成视频
  ↓
查看视频
  ↓
选择多个发布平台
  ↓
发布视频
  ↓
查看各平台发布结果
```

同时管理员能够：

```text
用户管理
+
AI 视频模型配置
+
发布平台配置
+
发布账号配置
+
日志查看
```

以上业务闭环全部正常后，本阶段任务才算完成。
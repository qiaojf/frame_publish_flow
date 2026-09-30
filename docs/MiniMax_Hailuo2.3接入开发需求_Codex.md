# MiniMax Hailuo 2.3 接入开发需求文档（Codex 直接执行版）

> 目标：在现有“AI 视频制作发布平台”中，优先只接入 **MiniMax Hailuo 2.3**，完成 Provider / Account / Model 配置、真实 Adapter、异步任务、状态查询、视频下载和本地保存所需的全部代码结构。
>
> 当前阶段：**先完成所有可配置和可开发内容，不执行真实视频生成，不消耗 API 余额。**
>
> 等用户后续充值后，再进行真实 API 端到端验证。
>
> 本文档基于 MiniMax Open Platform 当前官方 API 文档整理。

---

## 1. 你的角色

你是一名高级 Python / FastAPI 后端工程师和第三方 AI API 集成工程师。

请直接在现有项目中完成 MiniMax Hailuo 2.3 的接入。

不要新建第二套项目。

不要修改当前已经确定的总体技术栈：

```text
Python
FastAPI
PostgreSQL
SQLAlchemy
Alembic
Redis
Celery
Pydantic
FFmpeg
```

不要为了 MiniMax 单独绕开现有 Adapter 架构。

---

## 2. 本次开发范围

本次只接入一个真实视频生成模型：

```text
MiniMax Hailuo 2.3
```

Model ID：

```text
MiniMax-Hailuo-2.3
```

需要支持：

```text
文生视频 Text-to-Video
图生视频 Image-to-Video
```

暂时不接入：

```text
Google Veo
Runway
Seedance
Luma
其他 MiniMax 视频模型
```

但是必须继续遵守项目现有的可插拔 Adapter 设计，以后新增其他模型时不需要重写主流程。

---

## 3. 当前阶段禁止真实计费调用

当前用户已经创建 MiniMax Pay-as-you-go API Key，但暂时不充值。

因此本次 Codex 开发必须完成：

```text
数据库配置
Provider
Account
VideoModel
Secret 管理
MiniMax Adapter
请求参数转换
任务状态映射
Celery 任务结构
视频下载结构
Mock / 单元测试
管理员配置 API
连接参数校验
README
```

当前不要：

```text
真正调用 POST /v1/video_generation 创建计费任务
```

测试必须通过：

```text
Mock HTTP Response
或
HTTP Client Mock
```

完成。

后续用户明确要求“开始真实测试”后，才允许进行真实视频生成调用。

---

## 4. MiniMax 官方 API 基础信息

MiniMax API Base URL：

```text
https://api.minimax.io
```

认证：

```text
HTTP Bearer Auth
```

请求 Header：

```http
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

API Key 来自 MiniMax Open Platform：

```text
Pay-as-you-go
→ Access
→ Create new API Key
```

禁止：

- 把 API Key 写死在源代码
- 把 API Key 提交到 Git
- 把完整 API Key 返回给前端
- 把完整 API Key 写入日志

---

## 5. 模型配置继续采用三层结构

必须沿用项目已经确定的：

```text
ModelProvider
    ↓
ModelAccount
    ↓
VideoModel
```

本次 MiniMax 配置关系应为：

```text
MiniMax
└── MiniMax PoC Account
    └── MiniMax Hailuo 2.3
```

---

## 6. ModelProvider 配置

新增或 Seed 一个 Provider：

```text
name:
MiniMax

code:
minimax

adapter_family:
minimax

default_api_base_url:
https://api.minimax.io

auth_type:
bearer_token

enabled:
true
```

建议 `provider_capabilities`：

```json
{
  "video_generation": true,
  "async_task": true,
  "file_retrieve": true
}
```

不要把 API Key 放在 Provider 表。

---

## 7. ModelAccount 配置

在 MiniMax Provider 下创建：

```text
name:
MiniMax PoC Account

provider:
MiniMax

api_base_url:
继承 Provider 默认值

api_version:
v1

api_key:
由管理员配置

enabled:
true
```

数据库继续使用项目已有的 `model_accounts` 设计。

至少应支持：

```text
id
provider_id
name
account_identifier
api_base_url
api_version
api_key
extra_config JSONB
enabled
created_at
updated_at
```

API Key 属于 Account 级凭证。

同一 MiniMax Account 以后可以挂多个 MiniMax Model。

---

## 8. API Key 安全要求

管理员写入 API Key 后：

列表接口只能返回：

```text
********xxxx
```

或类似 masked 值。

例如：

```json
{
  "has_api_key": true,
  "api_key_masked": "********Ab12"
}
```

禁止返回原始 API Key。

更新 Account 时：

```text
api_key 为空
```

表示：

```text
保持现有 API Key 不变
```

不要因为编辑账号名称而把 API Key 清空。

服务端日志不得打印：

```text
Authorization Header
API Key
完整 request headers
```

---

## 9. VideoModel 配置

创建 Hailuo 2.3：

```text
name:
MiniMax Hailuo 2.3

code:
minimax_hailuo_2_3

model_id:
MiniMax-Hailuo-2.3

adapter_type:
minimax_hailuo23

model_account:
MiniMax PoC Account

supports_text_to_video:
true

supports_image_to_video:
true

enabled:
true
```

---

## 10. Hailuo 2.3 capabilities JSONB

建议保存：

```json
{
  "text_to_video": true,
  "image_to_video": true,
  "supports_first_frame": true,
  "prompt": {
    "required_for_text_to_video": true,
    "required_for_image_to_video": false,
    "max_length": 2000
  },
  "prompt_optimizer": {
    "supported": true,
    "default": true
  },
  "fast_pretreatment": {
    "supported": true,
    "default": false
  },
  "duration_mode": "enum",
  "durations": [6, 10],
  "resolutions": ["768P", "1080P"],
  "resolution_duration_matrix": {
    "768P": [6, 10],
    "1080P": [6]
  },
  "max_images": 1,
  "image": {
    "formats": ["jpg", "jpeg", "png", "webp"],
    "max_size_mb_exclusive": 20,
    "short_edge_min_exclusive": 300,
    "aspect_ratio_min": 0.4,
    "aspect_ratio_max": 2.5,
    "supports_public_url": true,
    "supports_base64_data_url": true
  },
  "camera_commands_supported": true,
  "callback_supported": true
}
```

Hailuo 2.3 的官方约束：

```text
6 秒：
768P 或 1080P

10 秒：
仅 768P
```

后端必须做组合校验。

禁止出现：

```text
10 秒 + 1080P
```

仍然向 MiniMax 提交的情况。

---

## 11. 默认请求参数

为了后续第一次真实 PoC 尽量简单，建议：

```json
{
  "duration": 6,
  "resolution": "768P",
  "prompt_optimizer": true,
  "fast_pretreatment": false
}
```

当前阶段只保存默认配置，不真实调用。

---

## 12. 官方 Text-to-Video 创建接口

Endpoint：

```text
POST https://api.minimax.io/v1/video_generation
```

Content-Type：

```text
application/json
```

最小请求结构：

```json
{
  "model": "MiniMax-Hailuo-2.3",
  "prompt": "A cinematic robot walking through Tokyo at night.",
  "duration": 6,
  "resolution": "768P"
}
```

官方返回核心结构：

```json
{
  "task_id": "106916112212032",
  "base_resp": {
    "status_code": 0,
    "status_msg": "success"
  }
}
```

Adapter 创建成功后必须保存：

```text
task_id
```

到系统：

```text
video_generation_tasks.provider_task_id
```

---

## 13. Text-to-Video 参数

Hailuo 2.3 至少支持：

```text
model
prompt
prompt_optimizer
fast_pretreatment
duration
resolution
callback_url
```

### model

从：

```text
VideoModel.model_id
```

读取。

不要只在 Adapter 内写死。

### prompt

文生视频必填。

最大：

```text
2000 characters
```

### prompt_optimizer

Boolean。

官方默认：

```text
true
```

### fast_pretreatment

Boolean。

当：

```text
prompt_optimizer = true
```

时可用于减少 Prompt 优化时间。

官方默认：

```text
false
```

### duration

Hailuo 2.3：

```text
6
10
```

### resolution

Hailuo 2.3：

```text
768P
1080P
```

但必须遵守 resolution-duration matrix。

---

## 14. Camera Commands

MiniMax Hailuo 2.3 支持 Prompt 中使用 Camera Command。

本次不需要单独创建复杂 UI。

后端只需要：

```text
允许 Prompt 原样传递
```

并在 capabilities 中标记：

```text
camera_commands_supported = true
```

官方支持的命令包括：

```text
[Truck left]
[Truck right]
[Pan left]
[Pan right]
[Push in]
[Pull out]
[Pedestal up]
[Pedestal down]
[Tilt up]
[Tilt down]
[Zoom in]
[Zoom out]
[Shake]
[Tracking shot]
[Static shot]
```

不要在后端擅自删除这些字符。

---

## 15. 官方 Image-to-Video 创建接口

图生视频和文生视频使用相同 Endpoint：

```text
POST https://api.minimax.io/v1/video_generation
```

区别是增加：

```text
first_frame_image
```

请求示例：

```json
{
  "model": "MiniMax-Hailuo-2.3",
  "prompt": "The person slowly walks toward the camera.",
  "first_frame_image": "https://example.com/input.jpg",
  "duration": 6,
  "resolution": "768P"
}
```

返回仍然是：

```text
task_id
```

因此不需要设计两套任务查询流程。

---

## 16. first_frame_image 支持方式

官方支持：

```text
公开 HTTP/HTTPS URL
或
Base64 Data URL
```

例如：

```text
data:image/jpeg;base64,...
```

输入图片要求：

```text
JPG
JPEG
PNG
WebP
```

文件大小：

```text
小于 20 MB
```

尺寸：

```text
短边 > 300px
```

宽高比：

```text
2:5 ～ 5:2
```

即：

```text
0.4 ～ 2.5
```

后端在提交 MiniMax 前应先进行本地校验。

---

## 17. 项目中的图生视频图片处理

现有平台前端上传图片后：

```text
Vue
↓
FastAPI
↓
Storage
↓
GenerationTask
```

MiniMax Adapter 可以采用两种方式：

### 方案 A：公网 URL

如果 Storage 可以生成 MiniMax 能访问的公网 URL：

```text
first_frame_image = public_url
```

### 方案 B：Base64 Data URL

本地 PoC 无公网 Storage 时：

```text
本地图片
↓
Base64
↓
data:image/...;base64,...
↓
first_frame_image
```

第一阶段本地 PoC 建议实现 Base64 Data URL 支持。

这样不需要为了 MiniMax 测试提前部署公网对象存储。

---

## 18. MiniMaxHailuo23Adapter

新增：

```text
backend/app/adapters/video_models/minimax_hailuo23.py
```

类：

```python
class MiniMaxHailuo23Adapter(VideoModelAdapter):
    ...
```

至少实现：

```python
async def create_text_to_video(...)
async def create_image_to_video(...)
async def get_task_status(...)
async def get_result(...)
async def test_connection(...)
```

如果基础 Adapter 当前定义不同，可以合理适配现有接口。

不要为了 MiniMax 重写所有 Adapter 基类。

---

## 19. HTTP Client

不要在各方法里散落：

```python
requests.post(...)
requests.get(...)
```

建议建立统一：

```text
MiniMaxClient
```

负责：

```text
Base URL
Authorization
Timeout
JSON
HTTP Error
MiniMax base_resp Error
Secret Sanitization
```

建议优先使用：

```text
httpx.AsyncClient
```

如果项目已有统一 HTTP Client，则复用。

---

## 20. 创建任务流程

系统内部：

```text
POST /api/v1/generation/tasks
↓
创建 video_generation_tasks
status = pending
↓
Celery Task
↓
加载 VideoModel
↓
加载 ModelAccount
↓
加载 ModelProvider
↓
AdapterFactory
↓
MiniMaxHailuo23Adapter
↓
POST /v1/video_generation
↓
获得 task_id
↓
provider_task_id = task_id
↓
status = processing
```

HTTP API 不等待视频生成结束。

---

## 21. 官方查询任务接口

Endpoint：

```text
GET https://api.minimax.io/v1/query/video_generation
```

必须携带 Query Parameter：

```text
task_id=<MiniMax task_id>
```

即：

```text
GET /v1/query/video_generation?task_id=123456
```

认证：

```http
Authorization: Bearer <API_KEY>
```

成功后可能返回：

```json
{
  "task_id": "176843862716480",
  "status": "Success",
  "file_id": "176844028768320",
  "video_width": 1920,
  "video_height": 1080,
  "base_resp": {
    "status_code": 0,
    "status_msg": "success"
  }
}
```

---

## 22. MiniMax 官方任务状态

官方状态：

```text
Preparing
Queueing
Processing
Success
Fail
```

映射到系统统一状态：

| MiniMax | 系统内部 |
|---|---|
| Preparing | pending |
| Queueing | pending |
| Processing | processing |
| Success | success |
| Fail | failed |

Adapter 中统一完成映射。

业务 Service 不直接判断厂商字符串。

---

## 23. Success 处理

当 MiniMax 返回：

```text
status = Success
```

并有：

```text
file_id
```

时，不要立即把系统任务视为最终成功。

继续执行：

```text
file_id
↓
Video Download API
↓
download_url
↓
下载 MP4
↓
保存到项目 Storage
↓
创建 Video
↓
GenerationTask = success
```

只有本地视频保存成功之后，系统任务才最终：

```text
success
```

---

## 24. 官方视频下载接口

Endpoint：

```text
GET https://api.minimax.io/v1/files/retrieve
```

必须传：

```text
file_id=<file_id>
```

即：

```text
GET /v1/files/retrieve?file_id=123456
```

认证：

```http
Authorization: Bearer <API_KEY>
```

返回核心结构：

```json
{
  "file": {
    "file_id": "123456",
    "bytes": 0,
    "created_at": 1700469398,
    "filename": "output_aigc.mp4",
    "purpose": "video_generation",
    "download_url": "https://..."
  },
  "base_resp": {
    "status_code": 0,
    "status_msg": "success"
  }
}
```

Adapter / Service 获取：

```text
file.download_url
```

然后下载视频。

---

## 25. 视频下载要求

获取 `download_url` 后：

```text
HTTP GET video
↓
校验 HTTP 状态
↓
流式下载
↓
保存 Storage
```

禁止：

```text
一次性把大视频全部加载到内存
```

建议使用流式下载。

本地文件路径建议：

```text
local-data/videos/
```

或复用项目现有 Storage Backend。

文件名使用 UUID，不要完全信任厂商 filename。

---

## 26. FFmpeg 后处理

下载完成后：

使用现有 FFmpeg 逻辑获取：

```text
duration
width
height
format
```

并生成：

```text
thumbnail
```

然后创建：

```text
videos
```

记录。

如果 MiniMax 已返回：

```text
video_width
video_height
```

可以保留为参考，但最终本地 Video Metadata 建议仍以实际下载文件为准。

---

## 27. Celery 轮询策略

当前阶段采用：

```text
Celery + Polling
```

不要 busy loop。

建议：

```text
创建任务
↓
等待 polling interval
↓
查询状态
↓
未完成
↓
Celery retry / reschedule
↓
再次查询
```

配置项：

```text
MINIMAX_POLL_INTERVAL_SECONDS
MINIMAX_GENERATION_TIMEOUT_SECONDS
MINIMAX_HTTP_TIMEOUT_SECONDS
```

禁止永久轮询。

超过系统 timeout：

```text
GenerationTask = timeout
```

---

## 28. MiniMax Callback

官方 Create Video API 支持：

```text
callback_url
```

MiniMax 会：

1. 首次发送包含 `challenge` 的 POST 请求
2. 服务端需要回显：

```json
{
  "challenge": "..."
}
```

3. 验证后，任务状态变化可通过 Callback 推送。

本阶段：

```text
Callback 设计为可选能力
```

第一阶段真实 PoC 先采用：

```text
Celery Polling
```

不要因为 Callback 增加公网部署依赖。

capabilities 中保留：

```text
callback_supported = true
```

以后生产环境可升级为：

```text
Callback + Polling fallback
```

---

## 29. 错误处理

至少区分：

```text
MINIMAX_AUTH_FAILED
MINIMAX_INSUFFICIENT_BALANCE
MINIMAX_INVALID_PARAMETER
MINIMAX_RATE_LIMITED
MINIMAX_TASK_FAILED
MINIMAX_TIMEOUT
MINIMAX_DOWNLOAD_FAILED
MINIMAX_SERVICE_UNAVAILABLE
```

不要直接把 MiniMax 原始 Stack Trace 返回前端。

第三方原始错误保留在服务端脱敏日志。

前端返回：

```text
error_code
message
```

---

## 30. base_resp 处理

MiniMax Response 中存在：

```json
{
  "base_resp": {
    "status_code": 0,
    "status_msg": "success"
  }
}
```

不能只看 HTTP 200。

MiniMax Client 必须同时检查：

```text
HTTP Status
+
base_resp.status_code
```

如果业务状态非成功，统一转换成项目异常。

---

## 31. AdapterFactory 注册

注册：

```python
"minimax_hailuo23": MiniMaxHailuo23Adapter
```

最终：

```text
VideoModel.adapter_type
↓
VideoModelAdapterFactory
↓
MiniMaxHailuo23Adapter
```

Service 不允许出现：

```python
if model.code == "minimax_hailuo_2_3":
```

这种厂商耦合逻辑。

---

## 32. 管理员配置 API

确保现有管理员 API 可以配置：

### Provider

```text
GET/POST/PATCH /api/v1/admin/model-providers
```

### Account

```text
GET/POST/PATCH /api/v1/admin/model-accounts
```

### Model

```text
GET/POST/PATCH /api/v1/admin/video-models
```

普通用户：

```text
GET /api/v1/video-models
```

只返回：

```text
enabled 模型
安全字段
capabilities
```

绝不返回 API Key。

---

## 33. MiniMax Account 测试功能

可以实现：

```text
POST /api/v1/admin/model-accounts/{id}/test
```

但是当前阶段：

**不要通过真正创建视频来测试连接。**

如果没有明确的免费健康检查接口，则当前 `test` 只验证：

```text
Provider 配置完整
Base URL 合法
API Key 已配置
HTTP Client 可以初始化
```

不要执行：

```text
POST /v1/video_generation
```

以避免产生费用。

返回可以明确：

```json
{
  "success": true,
  "credential_configured": true,
  "real_api_verified": false,
  "message": "MiniMax configuration is complete. Real API verification has not been performed."
}
```

不要误导用户说“连接成功”，如果实际上没有调用 MiniMax。

---

## 34. 前端模型能力数据

普通用户查询 MiniMax Hailuo 2.3 时：

建议返回：

```json
{
  "id": "...",
  "name": "MiniMax Hailuo 2.3",
  "code": "minimax_hailuo_2_3",
  "supports_text_to_video": true,
  "supports_image_to_video": true,
  "capabilities": {
    "durations": [6, 10],
    "resolutions": ["768P", "1080P"],
    "resolution_duration_matrix": {
      "768P": [6, 10],
      "1080P": [6]
    }
  }
}
```

前端根据该数据动态显示时长和分辨率。

不要前端硬编码 Hailuo 规则。

---

## 35. 参数校验示例

合法：

```text
6s + 768P
6s + 1080P
10s + 768P
```

非法：

```text
10s + 1080P
```

非法请求必须在调用 MiniMax 前被后端拒绝。

例如：

```json
{
  "success": false,
  "error_code": "INVALID_MODEL_PARAMETER_COMBINATION",
  "message": "MiniMax Hailuo 2.3 does not support 1080P for 10-second generation."
}
```

---

## 36. 当前阶段单元测试

不得真实调用 MiniMax。

使用：

```text
pytest
+
httpx MockTransport
或
respx
或
项目现有 Mock 方案
```

至少测试：

### Provider / Account / Model

- Provider 正常加载
- Account API Key 不泄露
- VideoModel 正常加载
- disabled Account 不允许生成
- disabled Model 不允许生成

### Text-to-Video

Mock MiniMax 返回：

```json
{
  "task_id": "test_task_001",
  "base_resp": {
    "status_code": 0,
    "status_msg": "success"
  }
}
```

验证：

```text
provider_task_id 保存正确
```

### Image-to-Video

验证：

```text
first_frame_image
```

正确传递。

测试：

```text
Public URL
Base64 Data URL
```

至少一种完整通过。

### 参数校验

测试：

```text
6 + 768P -> 成功
6 + 1080P -> 成功
10 + 768P -> 成功
10 + 1080P -> 拒绝
```

### Task Status

分别 Mock：

```text
Preparing
Queueing
Processing
Success
Fail
```

验证映射正确。

### Download

Mock：

```text
file_id
↓
download_url
↓
视频流
```

验证最终写入 Storage。

---

## 37. Mock 官方完整链路

测试必须模拟：

```text
POST /v1/video_generation
↓
task_id

GET /v1/query/video_generation
↓
Preparing

GET /v1/query/video_generation
↓
Processing

GET /v1/query/video_generation
↓
Success
+
file_id

GET /v1/files/retrieve
↓
download_url

GET download_url
↓
MP4 bytes

Storage
↓
Video
↓
GenerationTask success
```

这个流程通过后，才认为 MiniMax Adapter 的代码结构开发完成。

---

## 38. 真实 API 测试阶段（本次先不要执行）

等用户后续充值并明确要求测试时：

第一条真实任务固定为：

```text
Model:
MiniMax-Hailuo-2.3

Mode:
Text-to-Video

Duration:
6

Resolution:
768P

Prompt:
使用简单测试 Prompt
```

真实测试顺序：

```text
1. 创建任务
2. 得到 task_id
3. 查询状态
4. 得到 file_id
5. 获取 download_url
6. 下载 MP4
7. 保存 Storage
8. FFmpeg
9. Video DB
10. Vue 播放
```

未经用户明确确认，不要执行这一步。

---

## 39. `.env.example`

如果项目当前的 ModelAccount Secret 暂时仍从环境变量读取，则加入：

```env
MINIMAX_API_BASE_URL=https://api.minimax.io
MINIMAX_API_KEY=

MINIMAX_POLL_INTERVAL_SECONDS=10
MINIMAX_GENERATION_TIMEOUT_SECONDS=900
MINIMAX_HTTP_TIMEOUT_SECONDS=60
```

如果已经完全实现数据库 ModelAccount，API Key 可以不放 `.env`。

真实 `.env` 禁止提交。

---

## 40. README 必须增加 MiniMax 章节

至少写清：

```text
MiniMax Open Platform 注册
Pay-as-you-go Access
创建 API Key

Provider 配置
Account 配置
VideoModel 配置

Hailuo 2.3 capabilities

文生视频流程
图生视频流程

任务查询流程
文件下载流程

当前开发阶段为什么不真实调用 API

如何在充值后启用真实测试
```

---

## 41. 开发完成后的验收标准

### 配置

- [ ] MiniMax Provider 存在
- [ ] MiniMax Account 可以配置
- [ ] API Key 可以保存
- [ ] API Key 查询时脱敏
- [ ] Hailuo 2.3 Model 可以配置
- [ ] capabilities 正确

### Adapter

- [ ] MiniMaxHailuo23Adapter 存在
- [ ] AdapterFactory 可加载
- [ ] Text-to-Video Request 正确
- [ ] Image-to-Video Request 正确
- [ ] 状态查询正确
- [ ] 状态映射正确
- [ ] file_id 获取正确
- [ ] download_url 获取正确

### Task

- [ ] FastAPI 创建 GenerationTask
- [ ] Celery 接管异步流程
- [ ] provider_task_id 保存
- [ ] 成功后创建 Video
- [ ] 失败写 error_code / error_message
- [ ] Timeout 正确处理

### Storage

- [ ] 视频流式下载
- [ ] 本地 Storage 保存
- [ ] FFmpeg 获取元数据
- [ ] 缩略图生成

### Tests

- [ ] 不消耗真实 MiniMax 余额
- [ ] pytest Mock 全流程通过
- [ ] 10s + 1080P 被后端拦截
- [ ] API Key 不出现在日志和 API Response

---

## 42. 最终交付报告要求

完成开发后必须输出：

### 1. 修改文件

列出新增 / 修改文件。

### 2. 数据库

说明：

```text
ModelProvider
ModelAccount
VideoModel
```

实际配置方式。

### 3. MiniMax Adapter

说明实现的方法。

### 4. 官方 API

说明实现的三个主要 Endpoint：

```text
POST /v1/video_generation

GET /v1/query/video_generation?task_id=...

GET /v1/files/retrieve?file_id=...
```

### 5. Celery

说明异步状态流程。

### 6. Tests

给出实际：

```bash
pytest
```

结果。

### 7. 真实 API 调用状态

必须明确写：

```text
Real MiniMax generation call: NOT EXECUTED
```

如果本阶段未充值。

不要把 Mock 测试说成真实 MiniMax 成功。

### 8. 后续真实测试方法

给出充值后所需的最小测试步骤，但不要自行执行。

---

## 43. MiniMax 官方流程总结

最终实现流程必须对应：

```text
用户提交
↓
FastAPI

只有 Prompt
→ Text-to-Video

Prompt + Image
→ Image-to-Video

↓
GenerationTask
↓
Celery
↓
MiniMaxHailuo23Adapter

↓
POST /v1/video_generation

↓
task_id

↓
GET /v1/query/video_generation?task_id=...

↓
Preparing / Queueing / Processing

↓
Success

↓
file_id

↓
GET /v1/files/retrieve?file_id=...

↓
download_url

↓
下载 MP4

↓
Storage

↓
FFmpeg

↓
Video

↓
GenerationTask = success

↓
Vue 显示并播放
```

---

## 44. 最重要的开发约束

本次开发始终坚持：

```text
ModelProvider
    ↓
ModelAccount
    ↓
VideoModel
    ↓
VideoModelAdapter
```

以及：

```text
FastAPI
↓
Celery
↓
MiniMaxHailuo23Adapter
↓
MiniMax API
```

不要：

- 把 MiniMax API Key 放入 VideoModel
- 让前端直接调用 MiniMax
- 在 Service 中硬编码 MiniMax
- 用长 HTTP 请求等待视频生成
- 用 Mock 成功冒充真实 API 成功
- 未经用户确认就创建会产生费用的真实视频任务

---

## 45. MiniMax 官方文档参考

Text-to-Video：

https://platform.minimax.io/docs/api-reference/video-generation-t2v

Image-to-Video：

https://platform.minimax.io/docs/api-reference/video-generation-i2v

Query Video Generation Task：

https://platform.minimax.io/docs/api-reference/video-generation-query

Video Download：

https://platform.minimax.io/docs/api-reference/video-generation-download

Video Generation Guide：

https://platform.minimax.io/docs/guides/video-generation

MiniMax Open Platform：

https://platform.minimax.io/

如官方 API 后续变化，优先以最新官方文档修正 Adapter，但不要擅自改变项目的 Provider / Account / Model / Adapter / Celery 总体架构。

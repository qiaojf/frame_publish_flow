# Instagram 官方视频发布流程适配需求文档

> 用途：Codex 开发实施说明  
> 阶段：PoC / 技术验证  
> 日期：2026-09-15  
> 目标平台：Instagram  
> 接入方式：Instagram API with Instagram Login  
> 当前验证版本：Graph API `v26.0`

---

## 1. 本次开发目标

当前系统已经存在多个发布平台 Adapter，例如 YouTube、X 等，并已经存在：

```python
from typing import Any

from app.adapters.publishing.base import PublishRequest
from app.adapters.publishing.configured import ConfiguredPublishAdapter


class InstagramPublishAdapter(ConfiguredPublishAdapter):
    platform_label = "Instagram Graph API"

    def build_platform_payload(self, request: PublishRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "media_type": "REELS" if request.publish_type == "reel" else "VIDEO",
            "caption": request.platform_payload.get(
                "caption", request.content or request.description or ""
            ),
        }
        if request.platform_payload.get("video_url"):
            payload["video_url"] = request.platform_payload["video_url"]
        return payload
```

当前 Adapter 仅负责构造一次请求的 payload，**尚未适配 Instagram 官方视频发布的多步骤流程**。

本次开发只要求补充 Instagram 视频发布能力，不修改其他平台发布逻辑。

最终要求：

```text
PublishRequest
    ↓
InstagramPublishAdapter
    ↓
1. 创建 Reel Media Container
    ↓
2. 轮询 Container 处理状态
    ↓
3. FINISHED
    ↓
4. 调用 media_publish
    ↓
5. 返回 Instagram Media ID
```

---

## 2. 本次 PoC 范围

### 2.1 本次必须实现

只实现 Instagram Reel 视频发布流程：

1. 从现有平台配置读取：
   - Instagram User ID
   - Access Token
   - Graph API Version
2. 从 `PublishRequest` 获取：
   - 公网 `video_url`
   - caption
3. 创建 Instagram Media Container。
4. 保存接口返回的 `container_id`。
5. 查询 Container 状态。
6. 等待状态变为 `FINISHED`。
7. 调用 `/media_publish`。
8. 获取最终 Instagram `media_id`。
9. 将发布结果返回给现有发布系统。
10. 对 Meta API 错误进行结构化记录。
11. 日志中禁止输出完整 Access Token。

---

## 3. 本次明确不做

PoC 阶段不要扩大开发范围。

以下内容暂不实现：

- Instagram OAuth 登录流程
- Token 自动生成
- Token 自动刷新
- 多 Instagram 账号授权管理
- Meta App Review
- Advanced Access
- Business Verification
- 公司官网、Privacy Policy 等正式上线配置
- Webhook
- 评论管理
- 私信管理
- 图片发布
- Stories 发布
- Carousel 发布
- Instagram Insights
- 前端页面改造
- YouTube Adapter 修改
- X Adapter 修改
- Facebook Adapter 修改
- 其他发布平台逻辑修改

当前 Access Token 和 Instagram User ID 已经通过人工方式取得并验证可用。

---

## 4. 当前已经验证完成的前置条件

目前人工测试已经确认：

```http
GET https://graph.instagram.com/v26.0/me
```

携带当前 Access Token 可以正常返回 HTTP `200`。

当前 Token 已具备以下权限：

```text
instagram_business_basic
instagram_business_content_publish
```

因此 Codex 本次无需处理授权获取流程，只需要消费已有配置。

---

# 5. Instagram 官方视频发布核心流程

Instagram Reel 发布不能只调用一次 API。

必须按照以下顺序执行：

```text
video_url
   ↓
POST /{ig_user_id}/media
   ↓
container_id
   ↓
GET /{container_id}
   ↓
IN_PROGRESS
   ↓
继续轮询
   ↓
FINISHED
   ↓
POST /{ig_user_id}/media_publish
   ↓
media_id
```

---

## 6. Step 1：创建 Reel Media Container

### Endpoint

```http
POST https://graph.instagram.com/{api_version}/{ig_user_id}/media
```

例如：

```http
POST https://graph.instagram.com/v26.0/{ig_user_id}/media
```

### 必需参数

```text
media_type=REELS
video_url={PUBLIC_VIDEO_URL}
access_token={ACCESS_TOKEN}
```

### 可选参数

```text
caption
share_to_feed
```

PoC 建议：

```text
share_to_feed=true
```

### 示例

```bash
curl -X POST \
  "https://graph.instagram.com/v26.0/{IG_USER_ID}/media" \
  -F "media_type=REELS" \
  -F "video_url=https://example.com/test.mp4" \
  -F "caption=Instagram API test" \
  -F "share_to_feed=true" \
  -F "access_token={ACCESS_TOKEN}"
```

### 成功返回示例

```json
{
  "id": "18270815569115548"
}
```

该 `id` 是：

```text
container_id
```

不是最终 Instagram 帖子的 Media ID。

Adapter 必须保存这个值，供后续状态查询和发布使用。

---

# 7. video_url 要求

Instagram 不直接读取本地文件路径。

下面这些地址不能直接作为 `video_url`：

```text
C:\video\test.mp4
/opt/videos/test.mp4
http://localhost/test.mp4
http://127.0.0.1/test.mp4
http://192.168.x.x/test.mp4
```

必须使用 Meta 服务器能够访问的公网地址，例如：

```text
https://example.com/videos/test.mp4
```

PoC 当前允许使用 GitHub Pages 上的测试视频，例如：

```text
https://username.github.io/repository/test.mp4
```

发布前至少校验：

1. `video_url` 非空。
2. URL 使用 `http://` 或 `https://`。
3. PoC 推荐必须为 `https://`。
4. URL 应可以被公网直接读取。
5. 不依赖 Cookie。
6. 不依赖登录。
7. 不依赖公司 VPN。

本次 Adapter 不负责把本地文件自动上传到 GitHub Pages。

---

# 8. Step 2：查询 Container 状态

创建 Container 后不能立即调用 `media_publish`。

需要等待 Instagram 完成视频抓取和处理。

### Endpoint

```http
GET https://graph.instagram.com/{api_version}/{container_id}
```

Query：

```text
fields=status_code,status
access_token={ACCESS_TOKEN}
```

### 示例

```bash
curl \
  "https://graph.instagram.com/v26.0/{CONTAINER_ID}?fields=status_code,status&access_token={ACCESS_TOKEN}"
```

### 成功处理完成示例

```json
{
  "status_code": "FINISHED",
  "status": "Finished: Media has been uploaded and it is ready to be published.",
  "id": "18270815569115548"
}
```

---

# 9. Container 状态处理规则

Adapter 必须支持轮询，而不是创建 Container 后立刻发布。

建议默认配置：

```text
poll_interval_seconds = 5
processing_timeout_seconds = 300
http_timeout_seconds = 30
```

这些值应允许从配置覆盖，不要硬编码到业务逻辑深处。

处理规则：

### `FINISHED`

立即进入：

```text
POST /media_publish
```

### 尚未完成

如果 `status_code` 尚未进入 `FINISHED`：

```text
等待 poll_interval_seconds
→ 再查询
```

直到：

```text
FINISHED
```

或达到：

```text
processing_timeout_seconds
```

### API 明确返回失败

如果状态接口明确返回错误状态或 API error：

```text
停止轮询
→ 返回发布失败
```

### 超时

超过最大等待时间：

```text
停止轮询
→ 返回 PROCESSING_TIMEOUT
```

禁止无限循环。

---

# 10. Step 3：正式发布 Reel

只有 Container 状态为：

```text
FINISHED
```

后才能执行正式发布。

### Endpoint

```http
POST https://graph.instagram.com/{api_version}/{ig_user_id}/media_publish
```

### 参数

```text
creation_id={container_id}
access_token={ACCESS_TOKEN}
```

### 示例

```bash
curl -X POST \
  "https://graph.instagram.com/v26.0/{IG_USER_ID}/media_publish" \
  -F "creation_id={CONTAINER_ID}" \
  -F "access_token={ACCESS_TOKEN}"
```

### 成功返回示例

```json
{
  "id": "18012345678901234"
}
```

这里的：

```text
id
```

是最终：

```text
Instagram Media ID
```

和前面的：

```text
container_id
```

是两个不同概念。

代码中必须使用不同变量：

```python
container_id
media_id
```

不要统一使用 `id` 导致后续逻辑混淆。

---

# 11. 可选 Step 4：发布后验证

PoC 建议支持，但不作为第一阶段强制要求。

发布成功后可以查询：

```http
GET https://graph.instagram.com/{api_version}/{media_id}
```

例如字段：

```text
id
media_type
permalink
timestamp
```

如果接口成功返回 `permalink`，可以将其作为最终发布 URL 返回给系统。

如果当前 API/权限无法返回 `permalink`：

```text
只要 media_publish 返回 media_id
```

即可认为发布 API 已成功。

---

# 12. InstagramPublishAdapter 改造要求

## 12.1 不再只依赖 `build_platform_payload`

当前实现：

```python
def build_platform_payload(...)
```

只能满足“一次 HTTP 请求”的发布模式。

Instagram 视频发布是：

```text
create container
→ wait
→ publish
```

因此 `InstagramPublishAdapter` 需要实现 Instagram 专用发布流程。

Codex 应先检查：

```text
app/adapters/publishing/base.py
app/adapters/publishing/configured.py
其他现有 Adapter
```

确认当前统一发布接口的方法名称和返回类型。

然后在**不破坏公共 Adapter 接口**的前提下，对 `InstagramPublishAdapter` 做平台特化。

不要为了 Instagram 重写整个 publishing framework。

---

## 12.2 建议内部方法拆分

建议拆成类似：

```python
class InstagramPublishAdapter(ConfiguredPublishAdapter):

    async def publish(...):
        ...

    async def create_media_container(...):
        ...

    async def wait_for_container(...):
        ...

    async def get_container_status(...):
        ...

    async def publish_media(...):
        ...
```

具体函数签名以现有项目架构为准。

Codex 不需要强行使用上述名称，但必须保持相同职责分离。

---

# 13. PublishRequest 字段映射

当前 payload 构造方式中的 caption 优先级应保留：

```python
request.platform_payload.get(
    "caption",
    request.content or request.description or ""
)
```

即：

```text
platform_payload.caption
        ↓ 不存在
request.content
        ↓ 不存在
request.description
        ↓ 不存在
""
```

---

## 13.1 video_url

优先读取：

```python
request.platform_payload["video_url"]
```

如果不存在：

```text
直接返回参数错误
```

错误信息建议：

```text
Instagram video publishing requires platform_payload.video_url
```

本次 PoC 不在 Adapter 中实现本地视频上传。

---

## 13.2 media_type

现有代码：

```python
"REELS" if request.publish_type == "reel" else "VIDEO"
```

本次 Instagram 视频 PoC 要以官方 Reel 发布流程为准：

```text
media_type=REELS
```

推荐处理：

```text
publish_type == "reel"
    → REELS
```

如果现有系统统一把视频类型传成：

```text
video
```

PoC 可以将：

```text
video
```

作为 Reel 的兼容别名：

```text
video → REELS
```

但不要继续把普通视频自动构造成：

```text
media_type=VIDEO
```

除非项目中另有已经验证过的 Instagram Feed Video 发布需求。

本次需求只保证：

```text
REELS
```

流程。

---

# 14. share_to_feed

支持从：

```python
request.platform_payload.get("share_to_feed")
```

读取。

如果没有传：

```text
默认 true
```

建议逻辑：

```python
share_to_feed = request.platform_payload.get("share_to_feed", True)
```

---

# 15. Instagram 平台配置要求

复用现有平台配置机制。

至少需要：

```text
access_token
ig_user_id
api_version
```

建议支持：

```text
base_url
poll_interval_seconds
processing_timeout_seconds
http_timeout_seconds
```

默认值：

```text
base_url=https://graph.instagram.com
api_version=v26.0
poll_interval_seconds=5
processing_timeout_seconds=300
http_timeout_seconds=30
```

如果当前数据库中的平台配置支持 JSON / JSONB 扩展字段：

```text
优先复用现有字段
```

本次不要为了这些配置新增复杂的数据表。

---

# 16. Token 使用要求

PoC 阶段：

```text
Access Token 由管理员人工配置
```

Adapter 不负责：

```text
OAuth
token exchange
token refresh
```

但必须满足：

1. Token 从配置读取。
2. 禁止在源码硬编码。
3. 禁止完整打印到日志。
4. 错误日志如果包含 URL/query，应屏蔽 `access_token`。
5. API 异常响应中如果含敏感字段，日志输出前应脱敏。

---

# 17. HTTP Client 要求

优先复用项目已有 HTTP Client。

如果当前后端使用：

```text
httpx
```

继续使用 `httpx`。

如果已有：

```text
AsyncClient
```

不要另建一套 `requests` 同步实现。

要求：

```text
不要阻塞 FastAPI event loop
```

---

# 18. API 请求参数形式

Meta API 支持 query/form 等方式时，本项目优先保持安全和可维护性。

推荐：

```text
POST 参数使用 form/data
GET 参数使用 params
```

不要手工字符串拼接：

```text
?access_token=...
```

这样方便日志脱敏，也避免 URL 编码错误。

例如：

```python
params = {
    "fields": "status_code,status",
    "access_token": access_token,
}
```

---

# 19. 错误处理要求

Meta API 错误通常包含：

```json
{
  "error": {
    "message": "...",
    "type": "...",
    "code": 100,
    "error_subcode": 33,
    "fbtrace_id": "..."
  }
}
```

Adapter 不允许只返回：

```text
Instagram publish failed
```

需要尽可能保留：

```text
HTTP status
error.message
error.type
error.code
error_subcode
fbtrace_id
当前发布阶段
container_id（如果已有）
```

但禁止记录 Access Token。

---

# 20. 发布阶段标识

错误信息中应区分发生在哪一步。

建议：

```text
CREATE_CONTAINER
WAIT_CONTAINER
GET_CONTAINER_STATUS
PUBLISH_MEDIA
VERIFY_MEDIA
```

例如：

```text
platform=instagram
stage=CREATE_CONTAINER
http_status=400
meta_error_code=...
message=...
```

方便排查问题。

---

# 21. 不允许出现的错误行为

Codex 修改后必须避免以下问题。

### 21.1 把字符串 `CONTAINER_ID` 直接发送给 API

错误：

```text
/{CONTAINER_ID}
```

却没有用真实接口返回值替换。

必须使用：

```python
container_id = create_response["id"]
```

---

### 21.2 创建 Container 后立即 publish

错误：

```text
POST /media
POST /media_publish
```

必须：

```text
POST /media
GET container status
等待 FINISHED
POST /media_publish
```

---

### 21.3 混淆 container_id 和 media_id

必须区分：

```text
container_id
media_id
```

---

### 21.4 使用错误 Host

本项目当前走：

```text
Instagram API with Instagram Login
```

并且 PoC 已经实际验证：

```text
https://graph.instagram.com/v26.0/me
```

可正常返回 HTTP 200。

因此本次 Adapter 默认：

```text
https://graph.instagram.com
```

不要擅自切换成 Facebook Login 对应的旧流程。

---

### 21.5 Token 写入日志

禁止：

```text
logger.info(full_request_url)
```

如果 URL 中包含：

```text
access_token
```

---

### 21.6 无限轮询

必须存在：

```text
processing_timeout_seconds
```

---

# 22. Retry 策略

PoC 保持简单。

## Container 状态查询

以下情况允许继续重试：

```text
视频仍在处理中
临时网络错误
可恢复的 5xx
```

仍然必须受总超时限制。

## 创建 Container

如果请求已经拿到明确失败响应：

```text
返回失败
```

不要无限重复创建 Container。

## media_publish

`media_publish` 涉及真正发布内容。

如果发生：

```text
请求超时
连接中断
返回结果未知
```

不要无条件自动重复调用多次，以免产生重复内容。

PoC 可以直接返回：

```text
PUBLISH_RESULT_UNKNOWN
```

并保留 `container_id` 供人工排查。

---

# 23. 返回结果

必须复用当前项目已有统一 Publish Result 数据结构。

如果现有结构允许，成功结果至少包含：

```json
{
  "platform": "instagram",
  "success": true,
  "external_id": "{media_id}"
}
```

建议额外保存：

```json
{
  "container_id": "{container_id}",
  "media_id": "{media_id}",
  "permalink": null
}
```

如果公共结果模型没有这些字段：

```text
不要破坏其他平台接口
```

可放入现有：

```text
metadata
platform_payload
raw_response
```

等扩展字段。

具体以项目现有数据模型为准。

---

# 24. 发布失败结果

失败时至少应该能够让上层判断：

```text
平台
失败阶段
错误类型
错误信息
是否可重试
```

例如：

```json
{
  "platform": "instagram",
  "success": false,
  "stage": "WAIT_CONTAINER",
  "error_code": "PROCESSING_TIMEOUT",
  "message": "Instagram media container processing timed out"
}
```

不要因为 Instagram 失败影响其他 Adapter 的接口定义。

---

# 25. 建议的流程伪代码

```python
async def publish(request):

    config = load_instagram_config()

    video_url = get_video_url(request)
    caption = get_caption(request)

    validate(video_url, config)

    container_id = await create_media_container(
        ig_user_id=config.ig_user_id,
        video_url=video_url,
        caption=caption,
        media_type="REELS",
        share_to_feed=True,
    )

    await wait_until_finished(
        container_id=container_id,
        interval=5,
        timeout=300,
    )

    media_id = await publish_media(
        ig_user_id=config.ig_user_id,
        container_id=container_id,
    )

    return publish_success(
        external_id=media_id,
        metadata={
            "container_id": container_id,
            "media_id": media_id,
        },
    )
```

这只是流程说明。

Codex 必须基于当前项目实际：

```text
Base Adapter
ConfiguredPublishAdapter
PublishRequest
PublishResult
配置模型
HTTP client
异常模型
```

做适配，不要机械复制伪代码。

---

# 26. 单元测试要求

Codex 至少增加以下测试。

## Test 1：创建 Container 成功

Mock：

```json
{
  "id": "container_123"
}
```

验证：

```text
container_id == container_123
```

---

## Test 2：IN_PROGRESS → FINISHED

Mock：

第一次：

```json
{
  "status_code": "IN_PROGRESS"
}
```

第二次：

```json
{
  "status_code": "FINISHED"
}
```

验证：

```text
只在 FINISHED 后调用 media_publish
```

---

## Test 3：处理超时

持续返回未完成状态。

验证最终：

```text
PROCESSING_TIMEOUT
```

并且：

```text
media_publish 没有被调用
```

---

## Test 4：Container 创建失败

Mock Meta Error。

验证：

```text
返回结构化异常
media_publish 不执行
```

---

## Test 5：media_publish 成功

Mock：

```json
{
  "id": "media_456"
}
```

验证：

```text
external_id == media_456
```

---

## Test 6：video_url 缺失

验证：

```text
不调用 Meta API
直接返回参数错误
```

---

## Test 7：Access Token 不进入日志

验证：

```text
日志中不存在完整 token
```

---

# 27. PoC 实际联调测试

单元测试完成后，用真实配置进行一次测试。

测试输入示例：

```json
{
  "publish_type": "reel",
  "content": "Instagram API PoC",
  "platform_payload": {
    "video_url": "https://username.github.io/repository/test.mp4",
    "caption": "Instagram API PoC",
    "share_to_feed": true
  }
}
```

期望日志：

```text
Instagram create container started
Instagram container created: <container_id>
Instagram container status: IN_PROGRESS
Instagram container status: FINISHED
Instagram publish started
Instagram publish succeeded: <media_id>
```

日志中的 token 必须打码。

---

# 28. PoC 验收标准

满足以下全部条件即视为本阶段完成：

- [ ] 不影响 YouTube/X/其他 Adapter。
- [ ] Instagram 使用现有统一发布入口。
- [ ] 可以读取已有 `ig_user_id`。
- [ ] 可以读取已有 Access Token。
- [ ] 可以读取公网 `video_url`。
- [ ] 创建 Media Container 成功。
- [ ] 能获得真实 `container_id`。
- [ ] 能自动轮询处理状态。
- [ ] `FINISHED` 后自动调用 `media_publish`。
- [ ] 可以获得最终 `media_id`。
- [ ] Instagram 测试账号实际出现 Reel。
- [ ] 处理失败时可以看到 Meta 错误信息。
- [ ] Access Token 不出现在日志。
- [ ] Container 处理存在超时保护。
- [ ] 不引入 OAuth/App Review 等本次范围外功能。
- [ ] 现有自动发布/重新发布机制仍然正常。

---

# 29. Codex 实施原则

Codex 开始修改前必须先读取当前项目代码，重点检查：

```text
app/adapters/publishing/base.py
app/adapters/publishing/configured.py
app/adapters/publishing/instagram.py
其他平台 Adapter
PublishRequest
PublishResult
平台配置模型
发布 service
HTTP client
异常处理
现有 test
```

实施原则：

1. 尽量小范围修改。
2. 优先只修改 Instagram Adapter。
3. 必要时才给公共 Adapter 增加可复用扩展点。
4. 不允许为了 Instagram 破坏其他平台。
5. 不修改与本需求无关的前端。
6. 不重构整个 publishing 模块。
7. 保持当前代码风格。
8. 增加必要测试。
9. 修改后运行现有测试。
10. 最后提供修改文件列表和测试结果。

---

# 30. Codex 完成后必须输出

开发结束时给出：

```text
1. 修改了哪些文件
2. 每个文件修改目的
3. Instagram 最终发布流程
4. 新增/修改了哪些配置项
5. 如何运行单元测试
6. 如何进行真实 Instagram PoC
7. 实际 curl/API 对应关系
8. 仍未实现的内容
9. 已知风险
```

---

# 31. 官方资料参考

本需求基于 Meta 当前 Instagram API / 官方 Postman 文档整理。

Instagram API 官方 Postman Collection：

https://www.postman.com/meta/instagram/collection/6yqw8pt/instagram-api

Instagram API with Instagram Login：

https://www.postman.com/meta/instagram/folder/1z5vxzu/instagram-api-with-instagram-login

Meta 官方 Reels Publishing 文档（Postman）：

https://www.postman.com/meta/instagram/folder/y6xustx/reels-publishing

当前 Instagram Login 权限：

```text
instagram_business_basic
instagram_business_content_publish
```

旧的：

```text
business_basic
business_content_publish
```

已被 Meta 弃用，不应再用于新实现。

---

# 32. 本阶段最终目标

本阶段不是完成完整 Instagram 商业接入。

唯一目标是：

```text
现有发布系统
     ↓
InstagramPublishAdapter
     ↓
公网视频 URL
     ↓
创建 Container
     ↓
自动等待 FINISHED
     ↓
media_publish
     ↓
返回 media_id
     ↓
Instagram 实际出现 Reel
```

只要这一条链路稳定跑通，即认为 Instagram 视频自动发布 PoC 完成。

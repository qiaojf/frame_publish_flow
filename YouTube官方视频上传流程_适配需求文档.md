# YouTube 官方视频上传流程_适配需求文档

> 用途：Codex 开发实施说明  
> 阶段：PoC 已验证完成，进入现有后端 Adapter 适配阶段  
> 平台：YouTube  
> API：YouTube Data API v3  
> 日期：2026-09-25

## 1. 本次开发目标

当前系统后端已经存在多平台发布能力，例如 Instagram、YouTube、X、Facebook。

Instagram PoC 已完成；YouTube 手工 PoC 也已经验证完成：

```text
Google Cloud Project
→ 启用 YouTube Data API v3
→ OAuth 2.0
→ youtube.upload + youtube.readonly
→ 获取 access_token / refresh_token
→ videos.insert
→ resumable upload
→ 返回 video_id
→ YouTube Studio 出现视频
→ videos.list
→ processingDetails.processingStatus = succeeded
```

本次要求 Codex 在不破坏现有 Instagram / X / Facebook 等 Adapter 的前提下，将上述已经验证完成的 YouTube 官方视频上传流程适配到现有 `YouTubePublishAdapter`。

本次不是重新设计整个 publishing framework，而是补全 YouTube 平台专有流程。

## 2. 本次必须实现

1. 从现有平台/账号配置读取 YouTube OAuth 参数。
2. 支持 `access_token`。
3. 支持 `refresh_token`。
4. Access Token 过期后自动刷新。
5. 使用 `videos.insert` 上传本地视频。
6. 使用 resumable upload。
7. 支持上传进度。
8. 上传成功后取得 `video_id`。
9. 默认 `privacyStatus=private`。
10. 上传后调用 `videos.list` 查询处理状态。
11. 轮询 `processingDetails.processingStatus`。
12. 正确处理 `processing / succeeded / failed / terminated`。
13. 支持处理超时。
14. 返回现有统一 Publish Result。
15. 结构化处理 Google / YouTube API 错误。
16. 日志不得输出完整 Token。
17. 不影响 Instagram / X / Facebook Adapter。

## 3. 本次暂不实现

```text
正式 OAuth Web 登录页面
多 Google 账号授权 UI
Google OAuth Verification
YouTube API Audit
自动发布 Public 视频
定时发布 publishAt
Shorts 特殊业务规则
Playlist 自动添加
缩略图上传
字幕上传
评论管理
频道管理
直播
Analytics
前端大范围改造
```

## 4. 当前已验证的 OAuth Scope

PoC 已实际验证：

```text
https://www.googleapis.com/auth/youtube.upload
https://www.googleapis.com/auth/youtube.readonly
```

用途：

```text
youtube.upload
→ 上传视频

youtube.readonly
→ 查询账号视频信息和 processingDetails
```

PoC 中只使用 `youtube.upload` 时，`videos.insert` 可以成功，但查询 `processingDetails` 出现：

```text
403 insufficientPermissions
```

增加 `youtube.readonly` 并重新授权后，状态查询成功。

因此当前 Adapter 至少按以上两个 scope 设计。

## 5. OAuth 配置原则

YouTube 上传属于用户授权行为，不能只依赖 API Key，必须使用 OAuth 2.0。

当前 PoC 使用 Desktop OAuth Client 只是为了手工验证。正式后端后续建议使用 Web Application OAuth Client，但 Adapter 不应依赖 Desktop 模式。

### 平台配置建议

```json
{
  "client_id": "<GOOGLE_OAUTH_CLIENT_ID>",
  "client_secret": "<GOOGLE_OAUTH_CLIENT_SECRET>",
  "token_uri": "https://oauth2.googleapis.com/token",
  "api_service_name": "youtube",
  "api_version": "v3"
}
```

### 账号配置建议

```json
{
  "platform": "youtube",
  "account_name": "Qiao",
  "access_token": "<ACCESS_TOKEN>",
  "refresh_token": "<REFRESH_TOKEN>",
  "token_expiry": "<DATETIME>",
  "scopes": [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
  ]
}
```

原则：

```text
平台配置 = Google OAuth App / YouTube API 公共参数
账号配置 = 某个具体 YouTube 账号的 Token / Channel 信息
```

## 6. Refresh Token 与自动刷新

自动发布需要用户不在线时继续调用 API，因此 OAuth 必须支持 offline access。

授权时需要：

```text
access_type=offline
```

并取得：

```text
refresh_token
```

Access Token 过期时：

```text
读取 refresh_token
+ client_id
+ client_secret
+ token_uri
→ 刷新 access_token
→ 更新 token_expiry
→ 持久化新 token
→ 继续发布
```

不要要求管理员频繁手工更新 Access Token。

注意：Google 不保证每次授权/刷新都返回新的 `refresh_token`。更新账号配置时必须：

```python
if new_refresh_token:
    save(new_refresh_token)
else:
    keep_existing_refresh_token()
```

禁止因为响应中没有 `refresh_token` 就把数据库里的旧值清空。

## 7. OAuth Testing 状态限制

当前 PoC Google Auth Platform 处于 `Testing`。

对于 External App，测试用户授权通常约 7 天后失效；如果申请 offline access，测试状态下获得的 refresh token 也可能随授权一起失效。

因此：

```text
PoC 阶段可接受
正式部署前必须单独处理 OAuth App 正式发布 / Verification
```

不要把当前 PoC refresh token 当成永久凭证。

## 8. YouTube Channel 前置条件

PoC 中实际遇到：

```text
401 youtubeSignupRequired
```

原因是：

```text
Google 账号存在
但尚未创建 YouTube Channel
```

创建 Channel 后上传成功。

因此 Adapter 应将此错误转换为明确业务错误，例如：

```text
YOUTUBE_CHANNEL_REQUIRED
```

提示：

```text
当前 Google 账号尚未创建 YouTube Channel，请先创建频道并重新授权/重试。
```

## 9. 视频来源要求

Instagram 当前使用：

```text
公网 video_url → Meta 服务端抓取
```

YouTube 当前流程不同：

```text
本地/服务器视频文件 → 后端直接上传给 YouTube
```

因此 `YouTubePublishAdapter` 必须能获取本地实际文件路径。

Codex 应先检查现有：

```text
上传文件保存位置
发布任务对应文件路径
asset / media / attachment 模型
```

复用已有文件定位机制，不要为了 YouTube 再复制一套文件。

## 10. videos.insert 官方流程

核心调用：

```python
youtube.videos().insert(
    part="snippet,status",
    body=body,
    media_body=media,
)
```

等价 REST Endpoint：

```http
POST https://www.googleapis.com/upload/youtube/v3/videos
```

示例 body：

```json
{
  "snippet": {
    "title": "YouTube API PoC Test",
    "description": "Uploaded by YouTube Data API v3",
    "categoryId": "22"
  },
  "status": {
    "privacyStatus": "private"
  }
}
```

## 11. Resumable Upload

必须使用 resumable upload。

建议：

```python
media = MediaFileUpload(
    video_path,
    mimetype="video/mp4",
    resumable=True,
)
```

然后通过：

```python
request.next_chunk()
```

持续上传。

不要：

```text
一次把大视频全部读入内存
把视频转换成 Base64
```

## 12. 上传进度

`next_chunk()` 返回：

```text
status, response
```

当 `status` 非空时：

```python
progress_percent = int(status.progress() * 100)
```

建议日志：

```text
YouTube upload progress: 15%
YouTube upload progress: 48%
YouTube upload progress: 100%
```

如果现有任务表已有 `progress / percentage / status_detail`，优先复用，不要建立 YouTube 专用进度体系。

## 13. 上传成功返回 video_id

`videos.insert` 成功后读取：

```python
video_id = response["id"]
```

建议映射：

```text
external_id = video_id
```

代码中统一使用变量名：

```text
video_id
```

不要直接使用模糊的 `id`。

## 14. privacyStatus 默认策略

本阶段默认：

```text
private
```

建议：

```python
privacy_status = request.platform_payload.get(
    "privacy_status",
    "private"
)
```

允许：

```text
private
unlisted
public
```

但默认必须为 `private`。

Google 官方当前规定：2020-07-28 以后创建的未审核 API Project，通过 `videos.insert` 上传的视频会被限制为 private，完成 API Audit 后才能解除该限制。

因此 PoC 中视频为 Private 是正常现象，不应判定为 Adapter Bug。

## 15. metadata 字段

建议支持：

```text
title
description
categoryId
tags（可选）
privacyStatus
```

建议映射：

```text
title
→ request.title
→ 如当前模型无 title，按现有系统规则取得

description
→ request.description
→ 或 request.content

privacyStatus
→ request.platform_payload.privacy_status
→ 默认 private

categoryId
→ request.platform_payload.category_id
→ 默认 22
```

具体以当前 `PublishRequest` 为准，Codex 开发前必须先读取现有模型。

## 16. 完整发布流程

```text
PublishRequest
    ↓
加载 YouTube 平台配置
    ↓
加载 YouTube 账号配置
    ↓
构建 OAuth Credentials
    ↓
必要时刷新 Access Token
    ↓
持久化新 Token
    ↓
定位本地视频文件
    ↓
校验文件
    ↓
构建 snippet/status
    ↓
videos.insert
    ↓
resumable upload
    ↓
更新上传进度
    ↓
取得 video_id
    ↓
videos.list
    ↓
轮询 processingDetails
    ↓
succeeded
    ↓
返回 PublishResult
```

## 17. 建议的 Adapter 内部职责

建议拆分为类似：

```python
class YouTubePublishAdapter(...):

    async def publish(...):
        ...

    def build_credentials(...):
        ...

    def refresh_credentials_if_needed(...):
        ...

    def resolve_video_file(...):
        ...

    def build_video_body(...):
        ...

    def create_upload_request(...):
        ...

    def execute_resumable_upload(...):
        ...

    def get_processing_status(...):
        ...

    def wait_for_processing(...):
        ...
```

名称可按现有项目规范调整，重点是 OAuth、Upload、Processing Status、Result 职责分离。

## 18. FastAPI 异步注意事项

Google Python Client 的 `videos.insert` / `next_chunk()` 通常是同步阻塞调用。

如果当前发布 Service 是 async，不要直接长时间阻塞 FastAPI event loop。

Codex 必须先检查现有项目是否已有：

```text
线程池
asyncio.to_thread
BackgroundTasks
worker
Celery / RQ
自定义任务队列
```

优先复用现有机制，不要为了 YouTube 随意引入新的任务框架。

## 19. 上传重试

对以下情况允许有限重试：

```text
临时网络错误
部分 5xx
官方建议可重试错误
```

建议指数退避：

```text
1s
2s
4s
8s
16s
```

必须配置最大次数/最大等待时间，禁止无限重试。

以下错误不要无条件自动重复上传：

```text
OAuth 权限不足
账号没有 Channel
文件不存在
无效 metadata
配额限制
明确 4xx
refresh_token 失效
```

## 20. processingDetails 查询

上传成功获得 `video_id` 后：

```python
youtube.videos().list(
    part="processingDetails,status",
    id=video_id,
)
```

读取：

```text
processingDetails.processingStatus
```

官方状态：

```text
processing
succeeded
failed
terminated
```

### processing

继续等待并轮询。

### succeeded

发布流程成功。

### failed

读取：

```text
processingFailureReason
```

返回结构化失败，同时保留 `video_id`。

### terminated

不要当作成功。本阶段按“状态不可确认/异常”处理，并保留 `video_id` 供人工检查。

## 21. 状态轮询配置

建议默认：

```text
poll_interval_seconds = 5
processing_timeout_seconds = 600
```

必须允许配置覆盖。

如果超时：

```text
返回 PROCESSING_TIMEOUT
保留 video_id
不要重新上传视频
```

原因：`videos.insert` 已成功后，YouTube 后台可能仍继续转码。此时再次上传会产生重复视频。

## 22. Publish Result

必须复用现有统一发布结果。

成功至少：

```json
{
  "platform": "youtube",
  "success": true,
  "external_id": "<VIDEO_ID>"
}
```

建议 metadata：

```json
{
  "video_id": "<VIDEO_ID>",
  "privacy_status": "private",
  "processing_status": "succeeded",
  "watch_url": "https://www.youtube.com/watch?v=<VIDEO_ID>"
}
```

如果当前公共结果对象没有 metadata，使用项目现有扩展字段，不要破坏公共接口。

## 23. 失败结果

失败至少包含：

```text
platform
stage
error_code
message
retryable
video_id（如果已取得）
```

例如：

```json
{
  "platform": "youtube",
  "success": false,
  "stage": "PROCESSING",
  "error_code": "PROCESSING_TIMEOUT",
  "message": "YouTube video processing timed out",
  "retryable": true,
  "video_id": "xWbZkP6urV0"
}
```

## 24. 建议阶段标识

```text
LOAD_CONFIG
REFRESH_TOKEN
VALIDATE_FILE
CREATE_UPLOAD
UPLOAD_VIDEO
GET_VIDEO_ID
CHECK_PROCESSING
COMPLETE
```

## 25. OAuth / API 错误处理

### invalid_grant

可能：

```text
refresh_token 失效
用户撤销授权
Testing 授权过期
客户端凭证不匹配
```

转换：

```text
YOUTUBE_REAUTH_REQUIRED
```

### insufficientPermissions

PoC 已实际遇到：

```text
403 insufficientPermissions
```

转换：

```text
YOUTUBE_SCOPE_INSUFFICIENT
```

提示需要：

```text
youtube.upload
youtube.readonly
```

并重新 OAuth 授权。

### youtubeSignupRequired

PoC 已实际遇到：

```text
401 youtubeSignupRequired
```

转换：

```text
YOUTUBE_CHANNEL_REQUIRED
```

### quotaExceeded / dailyLimitExceeded

转换：

```text
QUOTA_EXCEEDED
```

停止重试。

### 其他至少区分

```text
401 Unauthorized
403 Forbidden
400 invalidRequest
404 videoNotFound
5xx temporary failure
network timeout
```

不要统一只返回 `YouTube publish failed`。

## 26. 日志安全

禁止打印：

```text
access_token
refresh_token
client_secret
Authorization header
完整 credentials JSON
```

允许打印：

```text
video_id
channel 名称
upload progress
processingStatus
error reason
```

Token 必须脱敏。

## 27. Token 持久化

Google Client 自动刷新后，如果：

```text
access_token
expiry
```

发生变化，需要写回账号配置/数据库。

如果没有返回新的 refresh token：

```text
保留已有 refresh_token
```

## 28. 文件校验

上传前至少：

```text
文件存在
文件可读
文件大小 > 0
```

可按现有系统能力检查 MIME type。

YouTube 官方 `videos.insert` 当前支持媒体类型：

```text
video/*
application/octet-stream
```

官方最大文件大小为 256GB，但如果系统本身已有更小限制，保持系统限制即可。

## 29. 与 Instagram Adapter 的边界

Instagram：

```text
公网 video_url
→ POST /media
→ container_id
→ FINISHED
→ media_publish
→ media_id
```

YouTube：

```text
本地 video file
→ videos.insert resumable upload
→ video_id
→ processingDetails
→ succeeded
```

不要为了表面统一强行让两个平台使用同一内部流程。

应该统一的是：

```text
PublishRequest
PublishResult
配置读取
错误模型
日志
任务状态
```

平台内部流程必须允许不同。

## 30. 不影响其他 Adapter 的要求

1. 优先只修改 `YouTubePublishAdapter`。
2. 公共层如需扩展，只做向后兼容修改。
3. 不修改 Instagram 已验证流程。
4. 不修改 X Adapter 行为。
5. 不修改 Facebook Adapter 行为。
6. 尽量不改变现有公共方法签名。
7. 如果必须修改公共接口，必须跑全部现有 Adapter 回归测试。

## 31. Codex 修改前必须检查

开始编码前读取：

```text
app/adapters/publishing/base.py
app/adapters/publishing/configured.py
app/adapters/publishing/youtube.py
app/adapters/publishing/instagram.py
app/adapters/publishing/x.py
PublishRequest
PublishResult
平台配置模型
账号配置模型
发布 service
后台任务逻辑
OAuth 工具
现有 tests
```

具体路径以项目实际结构为准。

禁止直接新建一套与现有 publishing framework 无关的独立模块。

## 32. 单元测试要求

至少新增：

### Test 1：正常上传

Mock 返回：

```json
{
  "id": "video_123"
}
```

验证：

```text
external_id == video_123
```

### Test 2：上传进度

模拟：

```text
10%
50%
100%
```

验证任务进度更新。

### Test 3：Token 自动刷新

```text
expired access_token
valid refresh_token
```

验证自动刷新、继续上传、保存新 token。

### Test 4：refresh token 失效

模拟 `invalid_grant`，验证：

```text
YOUTUBE_REAUTH_REQUIRED
```

且不继续上传。

### Test 5：processing → succeeded

验证只在 `succeeded` 后完成任务。

### Test 6：processing failed

验证：

```text
返回失败
保留 video_id
保存 processingFailureReason
```

### Test 7：processing timeout

验证：

```text
不重复 videos.insert
保留 video_id
返回 PROCESSING_TIMEOUT
```

### Test 8：youtubeSignupRequired

验证转换为：

```text
YOUTUBE_CHANNEL_REQUIRED
```

### Test 9：insufficientPermissions

验证转换为：

```text
YOUTUBE_SCOPE_INSUFFICIENT
```

### Test 10：文件不存在

验证不调用 YouTube API。

### Test 11：敏感信息日志

验证：

```text
access_token
refresh_token
client_secret
```

不会完整进入日志。

### Test 12：其他平台回归

必须跑现有：

```text
Instagram
X
Facebook
```

相关测试。

## 33. 真实联调

建议使用当前 PoC 已验证的视频。

输入：

```text
title = YouTube API PoC Test
description = Uploaded by YouTube Data API v3
privacy_status = private
```

期望：

```text
开始上传
→ progress
→ 100%
→ video_id
→ processing
→ succeeded
```

日志示例：

```text
YouTube publish started
YouTube OAuth credentials loaded
YouTube access token refreshed
YouTube upload started
YouTube upload progress: 25%
YouTube upload progress: 71%
YouTube upload progress: 100%
YouTube upload succeeded: video_id=xxxx
YouTube processing status: processing
YouTube processing status: succeeded
YouTube publish completed: video_id=xxxx
```

## 34. 第一阶段验收标准

- [ ] 统一发布入口可调用 YouTube Adapter。
- [ ] 能读取平台配置。
- [ ] 能读取账号配置。
- [ ] Access Token 过期后可使用 Refresh Token 刷新。
- [ ] 新 Access Token 和 expiry 可持久化。
- [ ] 能定位本地视频。
- [ ] `videos.insert` 上传成功。
- [ ] 使用 resumable upload。
- [ ] 能记录上传进度。
- [ ] 获得 `video_id`。
- [ ] 默认 `privacyStatus=private`。
- [ ] 能调用 `videos.list`。
- [ ] 能读取 `processingDetails`。
- [ ] `processingStatus=succeeded` 后任务成功。
- [ ] `failed` 有明确错误。
- [ ] processing timeout 不会重复上传。
- [ ] YouTube Studio 能看到视频。
- [ ] Token / Secret 不进入普通日志。
- [ ] Instagram 发布保持正常。
- [ ] X / Facebook 等 Adapter 不受影响。
- [ ] 现有自动发布/重新发布流程保持正常。

## 35. 当前 PoC 已验证结果

当前实际测试已经完成：

```text
YouTube Channel 创建成功
videos.insert 成功
YouTube Studio 出现测试视频
公开视频范围：Private
videos.list 成功
processingDetails.processingStatus = succeeded
```

期间已验证并解决：

```text
youtubeSignupRequired
→ 创建 YouTube Channel

insufficientPermissions
→ 增加 youtube.readonly
→ 重新 OAuth 授权
```

因此本次 Codex 工作不是继续探索 API，而是：

```text
将已经人工验证成功的官方流程工程化进入现有后端。
```

## 36. 后续阶段（本次不做）

```text
OAuth Web callback
多 YouTube 账号
Token 管理 UI
Google OAuth App Production
OAuth Verification
YouTube API Audit
public/unlisted 正式发布
publishAt
Shorts
缩略图
Playlist
Analytics
```

## 37. 官方文档参考

YouTube 官方上传指南：

https://developers.google.com/youtube/v3/guides/uploading_a_video

`videos.insert`：

https://developers.google.com/youtube/v3/docs/videos/insert

`videos.list`：

https://developers.google.com/youtube/v3/docs/videos/list

Video Resource / `processingDetails`：

https://developers.google.com/youtube/v3/docs/videos

视频状态实现指南：

https://developers.google.com/youtube/v3/guides/implementation/videos

YouTube OAuth Web Server：

https://developers.google.com/youtube/v3/guides/auth/server-side-web-apps

Google OAuth / Refresh Token：

https://developers.google.com/identity/protocols/oauth2

Google OAuth Testing / Audience：

https://support.google.com/cloud/answer/15549945

## 38. 最终目标

```text
现有发布系统
    ↓
YouTubePublishAdapter
    ↓
OAuth Credentials
    ↓
Access Token 自动刷新
    ↓
本地视频文件
    ↓
videos.insert
    ↓
Resumable Upload
    ↓
上传进度
    ↓
video_id
    ↓
videos.list
    ↓
processing
    ↓
succeeded
    ↓
统一 PublishResult
```

只要这一链路稳定跑通，并且不影响 Instagram、X、Facebook 等现有 Adapter，即视为 YouTube 视频上传 Adapter 第一阶段完成。

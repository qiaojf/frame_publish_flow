# API 清单

业务 API 基础前缀为 `/api/v1`，Swagger UI 为 `/docs`。除登录和根路径下的公开审核视频接口外，业务 API 均需 `Authorization: Bearer <token>`。

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET/HEAD | `/videos-pub/{id}`（无 `/api/v1` 前缀） | 公开 | 按视频 UUID 返回未删除的视频二进制，支持 Range；供发布平台拉取审核素材 |
| POST | `/auth/login` | 公开 | 登录并返回 JWT |
| GET | `/auth/me` | 登录 | 当前用户 |
| GET | `/video-models` | 登录 | 启用且安全字段的模型 |
| POST | `/generation/tasks` | 登录 | multipart 创建异步生成任务 |
| GET | `/generation/tasks` | 登录 | 自己的任务；管理员可查看全部 |
| GET | `/generation/tasks/{id}` | 所有者/管理员 | 生成任务详情 |
| GET | `/videos` | 登录 | 自己的视频；管理员可查看全部 |
| GET | `/videos/{id}` | 所有者/管理员 | 视频详情 |
| GET | `/videos/{id}/download` | 所有者/管理员 | 下载媒体文件 |
| DELETE | `/videos/{id}` | 所有者/管理员 | 软删除视频并清理当前媒体文件 |
| GET | `/publish/platforms` | 登录 | 启用平台及可用账号，不含 Secret |
| POST | `/publish/tasks` | 登录 | multipart 批量创建，每 target 一项任务 |
| GET | `/publish/tasks` | 登录 | 发布历史 |
| GET | `/publish/tasks/{id}` | 所有者/管理员 | 发布详情 |
| POST | `/publish/tasks/{id}/retry` | 所有者/管理员 | 仅重试 failed 单项任务 |
| GET/POST | `/admin/users` | admin | 用户列表/创建 |
| PATCH/DELETE | `/admin/users/{id}` | admin | 更新/删除用户 |
| POST | `/admin/users/{id}/reset-password` | admin | 重置密码 |
| GET/POST | `/admin/model-providers` | admin | 模型服务商列表/创建 |
| GET/PATCH/DELETE | `/admin/model-providers/{id}` | admin | 模型服务商详情/更新/删除 |
| GET/POST | `/admin/model-accounts` | admin | 模型接入账号列表/创建，Secret 只返回脱敏值 |
| GET/PATCH/DELETE | `/admin/model-accounts/{id}` | admin | 模型接入账号详情/更新/删除 |
| POST | `/admin/model-accounts/{id}/test` | admin | 校验账号启用状态和认证配置完整性 |
| GET/POST | `/admin/video-models` | admin | 模型列表/创建 |
| GET/PATCH/DELETE | `/admin/video-models/{id}` | admin | 模型详情/更新/删除 |
| POST | `/admin/video-models/{id}/test` | admin | 加载 Adapter 并校验模型配置 |
| GET/POST | `/admin/platforms` | admin | 平台列表/创建 |
| GET/PATCH/DELETE | `/admin/platforms/{id}` | admin | 平台详情/更新/删除 |
| GET/POST | `/admin/accounts` | admin | 发布账号列表/创建 |
| PATCH/DELETE | `/admin/accounts/{id}` | admin | 发布账号更新/删除 |
| POST | `/admin/accounts/{id}/test` | admin | 校验发布 Adapter、账号和 Token 状态 |
| GET | `/admin/logs` | admin | 审计日志 |

成功信封为 `{ "success": true, "data": ..., "message": null }`；分页为 `{ "items": [], "total": 0, "page": 1, "page_size": 20 }`；错误为 `{ "success": false, "data": null, "message": "...", "error_code": "..." }`。

发布请求的 `payload` 是 JSON 字符串，可附加 `cover` 文件。v2 使用 `common` 保存统一标题/正文/描述/标签，每个 target 使用 `publish_type=video|reel|post` 和独立 `overrides`。旧版顶层 `title/description/tags` 仍兼容。建议每次逻辑提交设置 `Idempotency-Key` 请求头；同一个 key 重发会返回原任务，不会重复发布。

生成状态固定为 `pending | processing | success | failed | cancelled | timeout`；发布状态固定为 `pending | publishing | success | failed | cancelled`。数据库、API 和前端均使用这些原始枚举，不做名称转换。

公开审核视频地址不对应前端页面，不返回标题、Prompt、作者等元数据。Docker/开发环境可使用 `http://localhost:5173/videos-pub/{video_id}` 验证；第三方平台无法访问本机 `localhost`，正式审核必须使用指向同一服务的公网 HTTPS 地址，例如 `https://publish.example.com/videos-pub/{video_id}`。视频被软删除或底层文件不存在时返回 404。

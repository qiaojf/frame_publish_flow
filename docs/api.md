# API 清单

基础前缀为 `/api/v1`，Swagger UI 为 `/docs`。除登录外均需 `Authorization: Bearer <token>`。

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
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
| GET/POST | `/admin/video-models` | admin | 模型列表/创建 |
| GET/PATCH/DELETE | `/admin/video-models/{id}` | admin | 模型详情/更新/删除 |
| GET/POST | `/admin/platforms` | admin | 平台列表/创建 |
| GET/PATCH/DELETE | `/admin/platforms/{id}` | admin | 平台详情/更新/删除 |
| GET/POST | `/admin/accounts` | admin | 发布账号列表/创建 |
| PATCH/DELETE | `/admin/accounts/{id}` | admin | 发布账号更新/删除 |
| GET | `/admin/logs` | admin | 审计日志 |

成功信封为 `{ "success": true, "data": ..., "message": null }`；分页为 `{ "items": [], "total": 0, "page": 1, "page_size": 20 }`；错误为 `{ "success": false, "data": null, "message": "...", "error_code": "..." }`。

发布请求的 `payload` 是 JSON 字符串，可附加 `cover` 文件。建议每次逻辑提交设置 `Idempotency-Key` 请求头；同一个 key 重发会返回原任务，不会重复发布。

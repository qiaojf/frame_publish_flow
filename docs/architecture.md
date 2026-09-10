# 架构说明

## 分层

```text
Vue 3
   | HTTPS / JWT
FastAPI API
   | 参数、认证、权限
Service
   | 业务规则、事务、审计
Adapter / Storage
   | 厂商隔离、文件持久化
PostgreSQL / Redis + Celery / Third-party API
```

API 不等待长耗时生成或发布完成：它在数据库创建任务后立即投递 Celery 并返回 202。Worker 使用独立 Session 执行 Adapter、更新单项任务状态并写入审计日志。

## 视频生成

`POST /api/v1/generation/tasks` 根据是否上传图片自动判定文生视频或图生视频。Service 验证模型启用状态及 duration、aspect ratio、resolution、image 能力；Worker 调用 `VideoModelAdapter`，保存结果文件，使用 FFprobe 读取元数据、FFmpeg 生成缩略图，最后创建 Video。

## 多平台发布

一次发布请求的每个 target 都创建一个独立 PublishTask。其 `idempotency_key` 对“请求 key + 平台 + 账号”求哈希并设唯一约束。单个平台失败不会回滚其他平台；重试接口只接受 failed 任务，success 任务在 Worker 入口直接跳过。

## Storage

`StorageBackend` 隔离文件存储。开发使用 `LocalStorageBackend`；S3/MinIO 配置入口已保留，未配置时会给出明确错误。数据库不保存图片或视频 Blob。

## 安全边界

JWT 鉴权和 admin/user RBAC 均在 FastAPI 依赖中执行。普通用户只能访问自己的任务和视频。密码使用 Argon2；模型 API Key 和发布账号 Secret 使用 Fernet 加密，响应只输出 masked 标记。结构化日志通过 request id 关联调用。

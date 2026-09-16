# 全项目联调测试

## 测试层次

1. `backend/tests/`：FastAPI、Service、真实 SQLAlchemy 关系、Celery eager 任务与 Mock Adapter 的自动回归；测试数据库与正式 PostgreSQL 配置隔离。
2. `backend/tests/test_end_to_end.py`：从登录开始，经生成、Storage、三目标发布、混合结果、幂等、失败重试、Audit Log 和 CORS 的单进程 API 闭环。
3. `scripts/verify-full-stack.ps1`：Docker 环境的一键真实基础设施验收，调用 `backend/scripts/integration_smoke.py`。

## 真实全栈验收

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify-full-stack.ps1
```

该验收不使用 SQLite、fakeredis 或同步 HTTP 任务替代基础设施。它验证：

- 数据库实际为 PostgreSQL 17，8 张表存在，JSONB、外键和索引可读取。
- Redis `PING` 成功。
- Celery Worker 响应，且注册 `generation.run`、`publish.run`。
- `ffmpeg` 和 `ffprobe` 命令可执行。
- Migration/Seed 后默认账号、Mock Model、Mock Platform、Mock Account 有效。
- 生成任务由 Worker 消费并产出可访问、可下载的视频。
- 三个 target 形成三个 PublishTask，混合结果互不回滚。
- 重复 HTTP 请求不增加任务；重试只更新失败任务。

脚本成功后不会停止容器，便于继续浏览器人工验收。失败时会输出 API 和 Worker 的最近日志。

## 外部平台边界

Mock Video Model 和 Mock Platform 用于本地闭环。YouTube、X、Instagram、WhatsApp 及其他真实 AI 模型仍需对应官方凭证、账号授权与 API 能力核验；没有凭证时测试不会伪造真实发布成功。

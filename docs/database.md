# 数据库说明

正式数据库为 PostgreSQL 17，结构由 SQLAlchemy ORM 与 Alembic initial Migration 同步维护。

| 表 | 作用 | 关键约束/索引 |
| --- | --- | --- |
| `users` | 用户与角色 | username 唯一；email 可选唯一；role/enabled 索引 |
| `video_models` | AI 模型配置与 capabilities | code 唯一；enabled 索引；API Key 加密 |
| `video_generation_tasks` | 单次生成任务 | user/model/status/time/provider task 索引 |
| `videos` | 生成后的视频资产元数据 | generation_task 唯一；owner/time/soft-delete 索引 |
| `publish_platforms` | 平台能力和 Adapter 配置 | code 唯一；enabled 索引 |
| `publish_accounts` | 平台下的账号 | platform/enabled 索引；凭证字段加密 |
| `publish_tasks` | 单平台发布任务 | 每行仅一个平台和账号；idempotency_key 唯一并索引 |
| `audit_logs` | 关键业务与管理操作 | user/action/resource/time 索引 |

视频采用软删除，避免破坏既有发布历史；外键使用 RESTRICT/SET NULL，未使用随意级联删除。JSONB 仅保存能力和扩展配置，主要关系保持标准外键。

初始化：

```powershell
cd backend
alembic upgrade head
python -m app.db.init_db
```

新增结构时应先修改 ORM，再执行 `alembic revision --autogenerate -m "说明"`，人工审阅生成内容后升级。不要手工维护第二套 SQL 建表脚本。

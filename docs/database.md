# 数据库说明

正式数据库为 PostgreSQL 17，结构由 SQLAlchemy ORM 与 Alembic Migration 同步维护。`20260909_0001` 创建初始结构，`20260910_0002` 对齐 ORM 约束与索引命名，`20260910_0003` 将模型服务商、接入账号和具体模型分层，并增强真实发布平台字段。迁移会回填旧模型数据，不要求清库。

| 表 | 作用 | 关键约束/索引 |
| --- | --- | --- |
| `users` | 用户与角色 | username 唯一；email 可选唯一；role/enabled 索引 |
| `model_providers` | 模型服务商公共配置 | code 唯一；adapter family/enabled 索引；不保存账号 Secret |
| `model_accounts` | 服务商下的接入账号与凭证 | provider/enabled 索引；API Key/Token 加密 |
| `video_models` | 具体模型、能力和请求默认值 | code 唯一；account/enabled 索引；不重复保存账号凭证 |
| `video_generation_tasks` | 单次生成任务 | user/model/status/time/provider task 索引 |
| `videos` | 生成后的视频资产元数据 | generation_task 唯一；owner/time/soft-delete 索引 |
| `publish_platforms` | 平台能力和 Adapter 配置 | code 唯一；enabled 索引 |
| `publish_accounts` | 平台下的账号 | platform/enabled 索引；凭证字段加密 |
| `publish_tasks` | 单平台发布任务及标准/平台载荷 | 每行仅一个平台和账号；idempotency_key 唯一并索引 |
| `audit_logs` | 关键业务与管理操作 | user/action/resource/time 索引 |

模型侧固定为 `ModelProvider → ModelAccount → VideoModel`，发布侧固定为 `PublishPlatform → PublishAccount`。视频采用软删除，避免破坏既有发布历史；外键使用 RESTRICT/SET NULL，未使用随意级联删除。JSONB 仅保存能力、标准载荷和扩展配置，主要关系保持标准外键。

初始化：

```powershell
cd backend
alembic upgrade head
python -m app.db.init_db
```

新增结构时应先修改 ORM，再执行 `alembic revision --autogenerate -m "说明"`，人工审阅生成内容后升级。不要手工维护第二套 SQL 建表脚本。

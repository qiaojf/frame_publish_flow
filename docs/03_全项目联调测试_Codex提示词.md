# 03_全项目联调测试_Codex提示词

## 一、你的角色

你是一名高级全栈联调、测试和部署工程师。

当前项目的：

```text
前端
+
后端
+
数据库
+
异步任务
```

已经分别开发完成或基本完成。

你的任务不是重新设计系统。

你的任务是：

```text
检查
↓
联调
↓
发现不一致
↓
修复
↓
测试
↓
让整个项目本地完整运行
```

---

# 二、项目技术栈

前端：

```text
Vue 3
TypeScript
Vite
Element Plus
Pinia
Vue Router
Axios
```

后端：

```text
Python
FastAPI
SQLAlchemy
Alembic
Pydantic
```

数据库：

```text
PostgreSQL 17
```

异步任务：

```text
Redis
Celery
```

文件：

```text
Local Storage
```

可扩展：

```text
MinIO / S3
```

视频处理：

```text
FFmpeg
```

---

# 三、最重要规则

## 规则 1

不要重新设计项目架构。

## 规则 2

不要创建第二套数据库。

## 规则 3

不要因为发现接口不一致，就大规模推翻前后端。

## 规则 4

优先做最小修改，使：

```text
需求
前端
API
ORM
数据库
Celery
```

一致。

## 规则 5

发现 Bug 直接修复，不只写报告。

## 规则 6

除非第三方真实 API 缺少凭证，否则不要用 Mock 掩盖前后端自身 Bug。

## 规则 7

Mock 只用于：

```text
AI Video Provider
Publish Platform
```

不能用于代替：

```text
数据库
FastAPI
Celery
权限
实际前后端接口
```

---

# 四、联调目标

必须最终跑通：

```text
Vue
↓
FastAPI
↓
PostgreSQL
↓
Redis
↓
Celery Worker
↓
Mock Video Model
↓
Storage
↓
Video
↓
Mock Publish Platform
↓
PublishTask
↓
Vue 发布记录
```

---

# 五、第一步：检查项目结构

确认至少存在：

```text
frontend/
backend/
docker-compose.yml
.env.example
README.md
```

检查：

- 前端是否可安装
- 后端依赖是否完整
- PostgreSQL 配置是否统一
- Redis 配置是否统一
- Celery 配置是否统一
- 文件目录是否可写
- FFmpeg 是否被正确调用

---

# 六、第二步：检查环境变量

检查：

```text
frontend .env
backend .env
docker-compose
```

重点确认：

```text
API Base URL
DATABASE_URL
REDIS_URL
CELERY_BROKER_URL
JWT_SECRET_KEY
STORAGE_PATH
CORS_ORIGINS
```

避免：

```text
localhost
127.0.0.1
Docker service name
```

混用导致连接错误。

如果：

前端在宿主机：

```text
http://localhost:xxxx
```

后端在 Docker：

注意端口映射。

如果后端和 PostgreSQL 都在 Compose：

数据库 Host 应使用 service name，不要写 localhost。

---

# 七、第三步：数据库迁移检查

执行：

```bash
alembic upgrade head
```

确认：

- migration 无错误
- 所有表创建
- 外键存在
- JSONB 正常
- Enum 正常
- 索引创建
- seed 可以执行

检查数据库至少有：

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

如果 ORM 与 migration 不一致：

修正 migration / ORM，使两者统一。

不要再创建第二套 schema。

---

# 八、第四步：初始化数据

确认至少存在：

```text
admin
Mock Video Model
Mock Platform
Mock Account
```

验证：

- admin 可以登录
- Mock Video Model enabled
- 支持 text_to_video
- 支持 image_to_video
- Mock Platform enabled
- Mock Account enabled

---

# 九、第五步：后端启动

检查：

```bash
uvicorn app.main:app --reload
```

或项目实际命令。

确认：

- FastAPI 正常启动
- `/docs` 可访问
- `/openapi.json` 正常
- 数据库连接正常
- Redis 连接正常
- CORS 正常

---

# 十、第六步：Celery 启动

检查 Worker。

例如：

```bash
celery -A app.tasks.celery_app worker -l info
```

以项目真实命令为准。

确认：

- Worker 能连接 Redis
- Generation Task 能被消费
- Publish Task 能被消费
- Task 注册正常
- 没有 import error

---

# 十一、第七步：前端启动

执行：

```bash
npm install
npm run dev
```

确认：

- 页面可打开
- API Base URL 正确
- Console 无关键错误
- 登录正常
- JWT 请求头正常

---

# 十二、API 契约一致性检查

重点核对：

```text
字段名
HTTP Method
URL
Query
Body
multipart/form-data
返回结构
分页
状态枚举
```

例如前端使用：

```text
model_id
```

后端不要返回：

```text
video_model_id
```

除非统一修改。

检查以下实体：

```text
User
VideoModel
GenerationTask
Video
PublishPlatform
PublishAccount
PublishTask
AuditLog
```

---

# 十三、状态枚举一致

Generation：

```text
pending
processing
success
failed
cancelled
timeout
```

Publish：

```text
pending
publishing
success
failed
cancelled
```

前端展示和后端状态必须完全匹配。

不要出现：

```text
backend: completed
frontend: success
```

类似不一致。

---

# 十四、登录权限联调

测试：

## Admin

- 登录
- `/auth/me`
- 访问管理页面
- 用户管理
- 模型管理
- 平台管理
- 账号管理
- 日志

## User

- 登录
- 视频制作
- 视频管理
- 发布
- 发布记录

User 请求管理员 API：

必须：

```text
403
```

User 访问其他用户视频：

必须拒绝。

---

# 十五、文生视频完整测试

场景：

```text
普通用户登录
↓
进入视频制作
↓
输入 Prompt
↓
不上传图片
↓
选择 Mock Video Model
↓
生成
```

必须确认：

1. 前端 multipart/form-data 正确
2. FastAPI 接收正确
3. 后端自动识别：

```text
text_to_video
```

4. 插入 `video_generation_tasks`
5. status = pending
6. 发送 Celery
7. Worker 调用 MockVideoModelAdapter
8. status -> processing
9. Mock 返回视频
10. Storage 保存
11. FFmpeg 获取元数据
12. 缩略图生成
13. 创建 videos
14. generation status -> success
15. 前端轮询到 success
16. 页面可以播放

任何一步失败：

定位并修复。

---

# 十六、图生视频完整测试

场景：

```text
Prompt
+
图片
+
Mock Video Model
```

确认后端识别：

```text
image_to_video
```

检查：

- 图片上传
- Storage
- source_image_url
- 模型能力
- Celery
- Video

---

# 十七、模型能力测试

验证：

模型 capabilities 例如：

```json
{
  "durations": [5, 10],
  "aspect_ratios": ["16:9", "9:16"],
  "resolutions": ["720p", "1080p"]
}
```

前端：

- 动态显示

后端：

- 再次校验

测试非法参数：

```text
duration=999
```

必须被拒绝。

---

# 十八、视频管理联调

验证：

- `/videos`
- `/videos/:id`
- 播放
- 下载
- 删除
- 用户权限

如果视频 URL 是相对路径：

确保前端能正确拼接。

如果使用 FastAPI 静态文件：

检查路由。

---

# 十九、多平台发布完整测试

至少准备三个 Mock Target。

例如：

```text
Mock Platform A
Mock Platform B
Mock Platform C
```

用户：

```text
选择 3 个平台
↓
发布
```

数据库必须产生：

```text
3 个 PublishTask
```

不是一个任务三个平台。

---

# 二十、混合发布结果

配置模拟：

```text
A = success
B = success
C = failed
```

验证：

- A success
- B success
- C failed
- A/B 不被回滚
- 前端分别展示状态
- C 显示错误信息

---

# 二十一、失败重试

用户对 C：

点击：

```text
重新发布
```

验证：

- 只 retry C
- 不重新创建 A/B
- 不重新调用 A/B
- C retry_count 增加
- C 最终可更新状态

---

# 二十二、幂等性测试

测试：

```text
快速双击发布
重复 HTTP 请求
Celery 自动重试
```

必须避免：

同一 PublishTask 重复发布成功两次。

如果发现重复发布风险：

修正幂等逻辑。

---

# 二十三、发布账号测试

平台：

```text
YouTube
```

多个账号：

```text
Company Official
Product Channel
```

确认：

- 前端选择账号
- account_id 正确提交
- 后端校验 account 属于 platform
- disabled account 不允许发布

---

# 二十四、Secret 安全检查

检查 API：

管理员模型列表、账号列表：

不得返回：

```text
完整 API Key
完整 Client Secret
完整 Access Token
完整 Refresh Token
```

日志：

不得出现上述值。

前端：

不得保存这些 Secret 到 LocalStorage。

---

# 二十五、Audit Log

确认重要动作有日志：

- login
- generation create
- generation success
- generation failed
- video delete
- publish create
- publish success
- publish failed
- retry
- admin config change

管理员页面可查看。

---

# 二十六、错误处理测试

模拟：

- PostgreSQL 连接失败
- Redis 连接失败
- Celery Worker 未启动
- 图片格式错误
- 图片超限
- Mock Model 失败
- Mock Publish 失败
- Token 过期
- disabled user
- disabled model
- disabled platform
- disabled account
- 无权限访问
- 视频不存在

确保：

- 前端有合理提示
- 后端不泄露 Stack Trace
- 服务端日志保留详细错误

---

# 二十七、前端 Build

执行：

```bash
npm run build
```

必须修复：

- TypeScript Error
- import Error
- Build Error

不要留下“开发模式能跑但 build 失败”。

---

# 二十八、后端测试

执行：

```bash
pytest
```

修复失败测试。

至少确保核心测试：

```text
Auth
Permission
Generation
Video
Publish
Retry
Idempotency
Admin
```

通过。

---

# 二十九、数据库回归

在空数据库环境重新执行：

```text
alembic upgrade head
```

再 Seed。

确保不是：

```text
只在开发人员旧数据库上能运行
```

---

# 三十、Docker Compose 检查

如果项目提供：

```text
docker-compose.yml
```

至少验证：

```text
PostgreSQL
Redis
```

能正常启动。

如果包含 backend / celery：

一并测试。

确保：

- 健康检查合理
- Volume 正常
- 端口无明显冲突
- Service name 正确

---

# 三十一、README 修正

README 必须能让新开发人员按步骤启动。

至少写清：

```text
1. 环境要求
2. clone
3. .env
4. docker compose up
5. alembic upgrade head
6. seed
7. backend
8. celery
9. frontend
10. login
11. Mock Video Model
12. Mock Platform
13. pytest
14. npm run build
```

不要只写概念说明。

---

# 三十二、联调时修改优先级

发现问题时按优先级：

```text
P0 无法启动
P0 数据库 migration 失败
P0 登录失败
P0 Celery 不消费任务
P0 生成链路不通
P0 发布链路不通

P1 权限错误
P1 API 字段不一致
P1 文件无法访问
P1 重试重复发布
P1 Secret 泄露

P2 UI 展示错误
P2 文案
P2 非关键样式
```

先修 P0，再 P1，再 P2。

---

# 三十三、不要做的事情

联调阶段禁止：

- 改用 MySQL
- 改用 React
- 改用 Django
- 改用 RabbitMQ
- 删除 Celery 改成长 HTTP
- 新增微服务
- 引入 Kubernetes
- 重做整套 UI
- 重建第二套数据库
- 无理由重命名所有 API
- 扩展第一阶段未要求的大量新功能

---

# 三十四、第一阶段完整验收流程

必须人工或自动至少验证一次：

```text
Admin 登录
↓
用户管理
↓
模型管理
↓
平台/账号管理
↓
创建普通用户

User 登录
↓
视频制作
↓
只有文字
↓
Mock Text-to-Video
↓
生成成功
↓
查看视频

User
↓
文字 + 图片
↓
Mock Image-to-Video
↓
生成成功
↓
查看视频

User
↓
选择多个 Mock Platform
↓
发布
↓
A success
B success
C failed
↓
查看发布记录
↓
retry C
↓
C success
```

全部跑通才算完成。

---

# 三十五、验收 Checklist

## Environment

- [ ] PostgreSQL 可用
- [ ] Redis 可用
- [ ] FFmpeg 可用
- [ ] `.env` 清楚

## DB

- [ ] migration
- [ ] seed
- [ ] FK
- [ ] index
- [ ] JSONB

## Backend

- [ ] FastAPI
- [ ] JWT
- [ ] Permission
- [ ] Celery
- [ ] Mock Video
- [ ] Storage
- [ ] FFmpeg
- [ ] Mock Publish
- [ ] Retry
- [ ] Idempotency

## Frontend

- [ ] Login
- [ ] Dashboard
- [ ] Video Create
- [ ] Task Status
- [ ] Videos
- [ ] Video Detail
- [ ] Publish
- [ ] Publish History
- [ ] Admin Pages

## Security

- [ ] user 不能 admin
- [ ] user 不能操作他人视频
- [ ] Secret 不泄露
- [ ] Password Hash

## Build/Test

- [ ] `npm run build`
- [ ] `pytest`
- [ ] 全链路测试

---

# 三十六、最终交付报告

完成联调后，必须输出：

## 1. 联调结果

明确：

```text
通过 / 未完全通过
```

## 2. 已修复问题

按：

```text
P0
P1
P2
```

列出。

## 3. 前后端接口一致性

说明修正项。

## 4. 数据库

给出：

- migration 结果
- seed 结果
- 表清单

## 5. Celery

给出：

- Worker 启动结果
- Generation Task
- Publish Task

## 6. 核心业务测试

分别说明：

- 文生视频
- 图生视频
- 多平台发布
- 混合成功/失败
- Retry
- 权限

## 7. Build/Test

给出实际执行：

```text
npm run build
pytest
```

以及结果。

## 8. 最终启动步骤

给出从空环境启动项目的完整命令。

## 9. 默认开发账号

明确说明。

## 10. 仍需用户提供的第三方凭证

例如：

```text
YouTube OAuth
X API
Instagram API
其他 AI Model API Key
```

如果没有真实测试：

明确写：

```text
尚未进行真实第三方平台发布验证
```

不要假装真实发布成功。

---

# 三十七、最终目标

## 多语言联调验收

- [ ] 登录页可以切换简体中文、日本語和 English
- [ ] 登录后正确恢复用户语言偏好
- [ ] 修改语言后 `users.preferred_locale` 正确保存
- [ ] 菜单、页面、管理后台与 Element Plus 组件同步切换
- [ ] 表单校验、视频生成状态、发布状态和错误提示同步切换
- [ ] `zh-CN`、`ja-JP`、`en-US` 不存在明显缺失 Key
- [ ] 页面刷新后语言保持，重新登录或更换设备后从用户偏好恢复

本阶段不是增加新功能，而是确保以下闭环真实可运行：

```text
登录
↓
视频生成
↓
异步任务
↓
视频资产
↓
视频预览
↓
多平台选择
↓
独立发布任务
↓
发布结果
↓
失败重试
↓
后台管理
```

最终要求：

```text
前端可用
+
后端可用
+
PostgreSQL 可用
+
Redis 可用
+
Celery 可用
+
Mock Model 可用
+
Mock Publish 可用
+
pytest 通过
+
npm run build 通过
```

做到这一点，本阶段才算完成。

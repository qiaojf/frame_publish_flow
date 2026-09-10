# 01_前端开发_Codex提示词

## 一、你的角色

你是一名高级前端架构师和 Vue 3 + TypeScript 开发工程师。

你的任务是为“AI 视频制作发布平台”完成前端开发。

本阶段只负责前端，不负责：
- 后端 FastAPI 实现
- PostgreSQL 数据库设计
- Redis / Celery
- AI 模型真实调用
- 第三方发布平台真实调用

如果后端接口尚未完成，可以基于本提示词定义的 API 契约进行前端开发，但不得通过前端 Mock 数据伪装成最终业务功能。

---

# 二、项目目标

平台用于：

1. AI 视频制作
   - 文生视频
   - 图生视频
   - 前端无需让用户手工选择“文生视频/图生视频”
   - 只有文字时，后端自动按文生视频处理
   - 文字 + 图片时，后端自动按图生视频处理

2. 视频资产管理
   - 查看
   - 预览
   - 下载
   - 删除
   - 重新生成

3. 视频多平台发布
   - X
   - Instagram
   - YouTube
   - WhatsApp
   - 其他可配置平台
   - 发布时可多选
   - 一个发布平台对应一个独立发布任务

4. 管理后台
   - 用户管理
   - AI 视频模型管理
   - 发布平台管理
   - 发布账号管理
   - 操作日志

---

# 三、固定技术栈

必须使用：

```text
Vue 3
TypeScript
Vite
Element Plus
Pinia
Vue Router
Axios
```

要求：

- 使用 Composition API
- 使用 `<script setup lang="ts">`
- 开启 TypeScript strict
- 尽量避免 `any`
- 统一 API 层
- 统一错误处理
- 统一路由权限控制
- 统一布局
- 不额外引入第二套大型 UI 框架
- 不使用 Nuxt
- 不使用 React

---

# 四、前端总体原则

前端只负责：

```text
页面展示
+
表单交互
+
文件上传
+
接口调用
+
状态展示
+
权限路由
+
任务轮询
```

前端禁止：

- 直接调用 AI 模型厂商 API
- 保存 API Key
- 保存 Client Secret
- 保存 Access Token
- 直接调用 YouTube / X / Instagram 等第三方平台 API
- 自己判断用户是否有后台权限后就完全信任该判断
- 在前端硬编码不同模型厂商的全部参数
- 在前端硬编码所有平台字段能力

所有真实业务规则以 FastAPI 返回结果为准。

---

# 五、用户角色

系统只包含：

```text
admin
user
```

## 普通用户

可以：

- 登录
- 视频制作
- 查看自己视频
- 下载自己视频
- 删除自己视频
- 重新生成
- 发布自己视频
- 多平台发布
- 查看自己的发布记录
- 重新发布失败任务

不能访问：

- 用户管理
- 模型管理
- 发布平台管理
- 发布账号管理
- 系统日志

## 管理员

拥有普通用户全部权限，并可访问系统管理页面。

---

# 六、页面结构

至少完成以下页面。

## 1. 登录

路由：

```text
/login
```

功能：

- 用户名
- 密码
- 登录按钮
- 登录错误提示
- 登录成功保存 JWT
- 自动获取当前用户
- 已登录状态访问 `/login` 时跳转首页

---

## 2. Dashboard

路由：

```text
/dashboard
```

普通用户显示：

- 我的视频数量
- 今日生成任务
- 生成中
- 发布成功
- 发布失败
- 最近生成视频
- 最近发布记录

管理员可额外显示：

- 用户总数
- 视频总数
- 总任务数量

第一版不做复杂 BI。

---

## 3. 视频制作

路由：

```text
/video/create
```

输入：

### 必填

- Prompt / 视频描述
- 视频生成模型

### 可选

- 参考图片
- 视频比例
- 视频时长
- 视频分辨率

要求：

- 图片支持 jpg / jpeg / png / webp
- 前端做基础类型校验
- 文件大小限制从配置或后端规则中获取，不要散落写死
- 上传前展示预览
- 可删除已选择图片

用户不需要手工选择：

```text
文生视频
图生视频
```

页面可显示提示：

```text
未上传图片：按文生视频处理
已上传图片：按图生视频处理
```

但最终判断以后端为准。

---

# 七、模型动态能力

模型下拉数据来自后端。

模型返回至少包括：

```ts
interface VideoModelOption {
  id: string
  name: string
  code: string
  supports_text_to_video: boolean
  supports_image_to_video: boolean
  capabilities: {
    durations?: number[]
    aspect_ratios?: string[]
    resolutions?: string[]
    max_images?: number
  }
}
```

前端根据 `capabilities` 动态显示：

- 时长
- 比例
- 分辨率

禁止写死：

```text
某模型只能 5 秒
某模型一定支持 1080p
```

如果上传了图片，但用户选择的模型不支持图生视频：

前端应明确提示并阻止提交。

如果未上传图片，但模型不支持文生视频：

前端应明确提示并阻止提交。

---

# 八、视频生成任务交互

点击“生成视频”后：

1. 调用后端创建生成任务
2. 成功后进入任务状态展示
3. 使用 HTTP Polling 查询状态
4. 默认每 3～5 秒轮询一次
5. 页面离开时停止无意义轮询
6. 状态完成后停止轮询

任务状态：

```text
pending
processing
success
failed
cancelled
timeout
```

界面显示：

- 等待中
- 生成中
- 成功
- 失败
- 已取消
- 已超时

如果后端无真实 progress：

不得伪造进度百分比。

可显示：

```text
生成处理中...
```

---

# 九、我的视频

路由：

```text
/videos
```

展示：

- 缩略图
- 标题
- 生成方式
- 使用模型
- 视频时长
- 创建时间
- 发布状态

建议支持：

- 卡片 / 表格切换，第一版可只做一种
- 关键词搜索
- 状态筛选
- 分页

操作：

- 播放
- 查看详情
- 下载
- 发布
- 重新生成
- 删除

删除必须二次确认。

---

# 十、视频详情

路由：

```text
/videos/:id
```

展示：

- 视频播放器
- 视频标题
- Prompt
- 参考图片
- 生成模型
- 生成类型
- 时长
- 分辨率
- 比例
- 创建时间
- 文件大小
- 视频尺寸
- 发布历史

操作：

- 下载
- 发布
- 重新生成
- 删除

---

# 十一、视频发布

路由：

```text
/publish
```

进入方式：

- 从视频详情进入
- 从视频列表进入

页面首先选择目标视频。

然后加载后端启用的平台和账号。

支持平台多选，例如：

```text
☑ X
☑ Instagram
☑ YouTube
☐ WhatsApp
```

每个平台如果存在多个账号：

必须允许选择发布账号。

例如：

```text
YouTube
  - 公司官方频道
  - 产品频道
```

---

# 十二、发布内容

公共字段：

- 标题
- 正文 / Description
- Tags / Hashtags
- 封面

系统允许：

```text
公共发布内容
+
平台级覆盖内容
```

例如：

```text
公共标题
公共描述

YouTube：
  使用公共内容

Instagram：
  覆盖 Caption

X：
  覆盖发布文字
```

不同平台具体字段能力从后端返回的：

```text
capabilities
```

动态生成。

禁止前端把所有平台字段完全写死。

---

# 十三、多平台发布行为

用户一次选择多个平台。

前端只提交一次发布请求。

后端负责拆分为：

```text
PublishTask A
PublishTask B
PublishTask C
```

前端展示每个平台自己的：

- 状态
- 错误
- 成功 URL

禁止把“整体发布成功”作为唯一状态。

---

# 十四、发布记录

路由：

```text
/publish/history
```

展示：

- 视频
- 平台
- 发布账号
- 状态
- 发布时间
- 发布 URL
- 错误信息

筛选：

- 平台
- 状态
- 日期
- 关键词

操作：

- 查看视频
- 打开发布 URL
- 重新发布失败任务

失败任务的“重新发布”只针对该任务。

---

# 十五、管理员页面

## 用户管理

路由：

```text
/admin/users
```

功能：

- 列表
- 新增
- 编辑
- 启用
- 禁用
- 删除
- 修改角色
- 重置密码

---

## AI 视频模型管理

路由：

```text
/admin/models
/admin/models/:id
```

显示：

- 模型名称
- code
- provider
- 是否支持文生视频
- 是否支持图生视频
- capabilities
- enabled

编辑配置时：

- API Key 等 Secret 只显示脱敏值
- 不能从普通查询接口得到完整值

模型配置字段以后端返回为准。

---

## 发布平台管理

路由：

```text
/admin/platforms
/admin/platforms/:id
```

功能：

- 新增
- 修改
- 启用
- 禁用
- 查看 capabilities
- 配置 adapter_type
- 配置 API Base URL

---

## 发布账号管理

路由：

```text
/admin/accounts
```

功能：

- 选择平台
- 账号名称
- account_identifier
- Client ID
- Client Secret
- Access Token
- Refresh Token
- Token 过期时间
- enabled

所有 Secret：

- 列表中脱敏
- 编辑页不能自动回填完整 Secret
- 后端如采用“留空表示不修改”策略，前端需兼容

---

## 操作日志

路由：

```text
/admin/logs
```

支持：

- 用户
- 操作类型
- 资源类型
- 时间
- 结果

日志只读。

---

# 十六、前端目录结构

推荐：

```text
frontend/
├── src/
│   ├── api/
│   │   ├── auth.ts
│   │   ├── users.ts
│   │   ├── models.ts
│   │   ├── generation.ts
│   │   ├── videos.ts
│   │   ├── platforms.ts
│   │   ├── publish.ts
│   │   └── logs.ts
│   │
│   ├── assets/
│   ├── components/
│   ├── layouts/
│   ├── router/
│   ├── stores/
│   ├── types/
│   ├── utils/
│   ├── views/
│   ├── App.vue
│   └── main.ts
│
├── package.json
├── vite.config.ts
└── tsconfig.json
```

允许小幅调整，但要保持职责清晰。

---

# 十七、API 请求封装

统一：

```text
src/utils/request.ts
```

至少实现：

- API Base URL
- Authorization Header
- JWT 自动注入
- 401 统一退出
- 403 权限提示
- 网络错误提示
- 超时处理
- 后端业务错误统一解析

禁止每个页面自己创建 Axios 实例。

---

# 十八、状态管理

Pinia 至少包括：

```text
authStore
```

保存：

- token
- 当前用户
- 登录状态
- 角色

根据实际需要增加：

```text
appStore
generationStore
```

不要把所有服务端数据都永久放入 Pinia。

---

# 十九、路由权限

实现：

```text
requiresAuth
requiresAdmin
```

前端路由守卫必须：

- 未登录跳 `/login`
- user 访问 `/admin/*` 时跳转无权限页面或 dashboard
- admin 正常访问

但必须明确：

```text
前端路由权限只是用户体验层
真正权限由后端校验
```

---

# 二十、TypeScript 类型

建立：

```text
src/types/
```

至少：

```text
auth.ts
user.ts
video-model.ts
generation.ts
video.ts
platform.ts
publish.ts
common.ts
```

尽量与后端 Schema 对齐。

公共分页类型示例：

```ts
interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
```

---

# 二十一、后端 API 契约

统一 API 前缀：

```text
/api/v1
```

前端至少按以下能力开发。

## Auth

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

## Models

```text
GET /api/v1/video-models
```

## Generation

```text
POST /api/v1/generation/tasks
GET  /api/v1/generation/tasks/{id}
GET  /api/v1/generation/tasks
```

## Videos

```text
GET    /api/v1/videos
GET    /api/v1/videos/{id}
DELETE /api/v1/videos/{id}
```

## Publish

```text
GET  /api/v1/publish/platforms
POST /api/v1/publish/tasks
GET  /api/v1/publish/tasks
GET  /api/v1/publish/tasks/{id}
POST /api/v1/publish/tasks/{id}/retry
```

## Admin

```text
GET/POST/PATCH/DELETE /api/v1/admin/users
GET/POST/PATCH/DELETE /api/v1/admin/video-models
GET/POST/PATCH/DELETE /api/v1/admin/platforms
GET/POST/PATCH/DELETE /api/v1/admin/accounts
GET /api/v1/admin/logs
```

如果实际后端接口与此略有差异：

联调阶段统一修正。

---

# 二十二、统一返回结构

兼容以下结构：

成功：

```json
{
  "success": true,
  "data": {},
  "message": null
}
```

失败：

```json
{
  "success": false,
  "data": null,
  "message": "错误信息",
  "error_code": "XXX"
}
```

分页：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

页面层不应反复解析不同风格的数据结构。

---

# 二十三、文件上传

上传图片时使用：

```text
multipart/form-data
```

必须：

- 校验类型
- 校验大小
- 支持预览
- 上传失败可重试
- 提交中禁用重复提交

---

# 二十四、UI 风格

整体：

```text
简洁
现代
企业后台
清晰
低学习成本
```

重点：

- 表单清楚
- 状态清楚
- 视频预览清楚
- 错误清楚
- 后台配置清楚

不要：

- 大量动画
- 复杂渐变
- 花哨营销视觉
- 不必要的大图背景

---

# 二十五、状态展示

使用 Element Plus：

```text
Tag
Badge
Progress
Alert
Result
```

状态统一：

```text
pending
processing
success
failed
cancelled
timeout
```

每个状态应统一样式。

---

# 二十六、错误体验

至少处理：

- 登录失败
- Token 过期
- 无权限
- 图片格式不支持
- 图片过大
- 模型不支持当前生成方式
- 视频生成失败
- 视频不存在
- 发布失败
- 发布账号失效
- API 请求失败
- 网络中断

错误信息必须尽量使用后端返回的用户可读 message。

---

# 二十七、第一阶段明确不做

不要开发：

- 在线视频剪辑器
- 时间轴
- AI 数字人
- AI 配音
- 自动字幕
- 自动脚本生成
- 自动 Prompt 优化
- 视频模板市场
- 定时发布
- 评论管理
- 私信管理
- BI
- 审批流程
- 移动 App

---

# 二十八、开发顺序

按以下顺序：

## Phase 1

- Vite + Vue 3 + TS
- Element Plus
- Router
- Pinia
- Axios
- 基础 Layout

## Phase 2

- 登录
- Auth Store
- 路由权限
- 用户菜单

## Phase 3

- Dashboard
- 视频制作页面
- 模型动态能力

## Phase 4

- 生成任务状态
- 轮询
- 我的视频
- 视频详情

## Phase 5

- 发布页面
- 平台多选
- 账号选择
- 公共内容 + 平台覆盖
- 发布记录
- 重试

## Phase 6

- 管理员用户管理
- 模型管理
- 平台管理
- 账号管理
- 日志

## Phase 7

- 完整联调准备
- Build
- 类型检查
- 清理问题

---

# 二十九、验收标准

必须满足：

## 登录

- [ ] admin 可登录
- [ ] user 可登录
- [ ] Token 正常
- [ ] 401 可退出
- [ ] user 不可进入后台

## 视频制作

- [ ] Prompt 可输入
- [ ] 图片可选
- [ ] 模型下拉从 API 加载
- [ ] 能力动态展示
- [ ] 模型能力不匹配时可提示
- [ ] 可以创建生成任务
- [ ] 可以轮询状态

## 视频

- [ ] 视频列表
- [ ] 视频详情
- [ ] HTML5 播放
- [ ] 下载
- [ ] 删除
- [ ] 重新生成入口

## 发布

- [ ] 多平台选择
- [ ] 多账号选择
- [ ] 公共发布内容
- [ ] 平台覆盖内容
- [ ] 创建发布任务
- [ ] 查看各平台独立状态
- [ ] 失败任务可重试

## 管理

- [ ] 用户管理
- [ ] 模型管理
- [ ] 平台管理
- [ ] 账号管理
- [ ] 日志

## 工程

- [ ] `npm install` 成功
- [ ] `npm run build` 成功
- [ ] 无明显 TS 错误
- [ ] 无关键 Console Error
- [ ] README 有前端启动方法

---

# 三十、最终交付

开发结束后输出：

1. 完成页面清单
2. 前端目录结构
3. API 模块清单
4. 路由清单
5. Pinia Store 清单
6. 已实现权限逻辑
7. 视频任务轮询实现说明
8. 多平台发布交互实现说明
9. `npm run build` 实际结果
10. 尚未完成或需后端联调的项目

不要只回答“完成”。

---

# 三十一、最重要的前端原则

始终遵循：

```text
Vue 页面
   ↓
API Client
   ↓
FastAPI
```

不要：

```text
Vue
 ↓
直接调用 AI 模型
```

也不要：

```text
Vue
 ↓
直接调用 YouTube / X / Instagram API
```

所有模型、平台、账号、权限、任务状态的真实业务逻辑统一由后端负责。

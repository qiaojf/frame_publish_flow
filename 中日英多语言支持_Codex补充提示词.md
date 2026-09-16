# 中 / 日 / 英多语言支持补充开发要求

## 一、目标

当前系统必须支持以下三种语言：

```text
zh-CN  简体中文
ja-JP  日本語
en-US  English
```

多语言属于系统基础能力。

必须覆盖：

- 登录页面
- Dashboard
- 视频制作
- 视频管理
- 视频详情
- 视频发布
- 发布记录
- 用户管理
- 模型 Provider 管理
- 模型 Account 管理
- 视频模型管理
- 发布平台管理
- 发布账号管理
- 操作日志
- 表单
- 按钮
- 菜单
- 状态
- 校验提示
- 错误提示
- 成功提示
- 确认框
- 空数据提示
- 分页
- 日期时间显示

禁止只翻译菜单而页面内部仍然存在大量硬编码文字。

---

# 二、总体原则

采用：

```text
前端 UI 国际化
+
用户语言偏好
+
后端稳定 error_code
+
必要的后端消息国际化
```

整体结构：

```text
User
 ↓
preferred_locale
 ↓
Vue i18n
 ↓
HTTP Accept-Language
 ↓
FastAPI
```

系统任何业务逻辑都不能依赖显示语言。

例如：

数据库状态必须保存：

```text
pending
processing
success
failed
```

不能保存：

```text
处理中
処理中
Processing
```

显示时再根据当前语言翻译。

---

# 三、前端技术

Vue 3 项目增加：

```text
vue-i18n
```

建议使用：

```text
Vue I18n 9+
Composition API
```

不要自己实现简单字典替换系统。

---

# 四、前端语言目录

建议：

```text
src/
└── locales/
    ├── index.ts
    ├── zh-CN.ts
    ├── ja-JP.ts
    └── en-US.ts
```

也可以按模块拆分：

```text
src/locales/
├── zh-CN/
│   ├── common.ts
│   ├── auth.ts
│   ├── video.ts
│   ├── publish.ts
│   └── admin.ts
│
├── ja-JP/
│   ├── common.ts
│   ├── auth.ts
│   ├── video.ts
│   ├── publish.ts
│   └── admin.ts
│
└── en-US/
    ├── common.ts
    ├── auth.ts
    ├── video.ts
    ├── publish.ts
    └── admin.ts
```

如果项目规模较大，优先采用按模块拆分方式。

---

# 五、禁止硬编码界面文字

错误示例：

```vue
<el-button>生成视频</el-button>
```

正确方式：

```vue
<el-button>
  {{ t('video.generate') }}
</el-button>
```

例如：

```typescript
const { t } = useI18n()
```

语言文件：

```typescript
// zh-CN
{
  video: {
    generate: '生成视频'
  }
}
```

```typescript
// ja-JP
{
  video: {
    generate: '動画を生成'
  }
}
```

```typescript
// en-US
{
  video: {
    generate: 'Generate Video'
  }
}
```

所有用户可见系统文字原则上必须进入 i18n。

---

# 六、语言 Key 设计

禁止使用中文本身作为 key：

```text
"生成视频": "動画を生成"
```

应该使用稳定的业务 Key：

```text
video.generate

video.prompt
video.model
video.duration
video.resolution

publish.publish
publish.platform
publish.account

status.pending
status.processing
status.success
status.failed
```

这样以后修改中文文案不会影响代码。

---

# 七、语言切换

系统顶部增加：

```text
语言 / Language / 言語
```

切换选项：

```text
简体中文
日本語
English
```

建议显示：

```text
中文
日本語
English
```

切换语言后：

必须立即刷新当前页面文字。

不要求整个页面重新加载。

---

# 八、语言选择优先级

未登录状态：

```text
1. LocalStorage 中上次选择语言
2. 浏览器 navigator.language
3. 系统默认语言
```

浏览器映射：

```text
zh-* → zh-CN
ja-* → ja-JP
en-* → en-US
其他 → 系统默认语言
```

登录之后：

优先级改成：

```text
1. 用户 preferred_locale
2. LocalStorage
3. 浏览器语言
4. 系统默认语言
```

系统默认语言必须可配置。

例如：

```text
VITE_DEFAULT_LOCALE=ja-JP
```

不要在代码内部写死。

---

# 九、数据库增加用户语言偏好

`users` 表增加：

```text
preferred_locale
```

允许值：

```text
zh-CN
ja-JP
en-US
```

建议默认值：

由系统配置决定。

例如：

```text
ja-JP
```

但不要将默认语言永久硬编码在数据库业务代码中。

---

# 十、用户语言 API

当前用户接口：

```text
GET /api/v1/auth/me
```

返回：

```json
{
  "id": "...",
  "username": "user01",
  "role": "user",
  "preferred_locale": "ja-JP"
}
```

增加修改语言：

```text
PATCH /api/v1/users/me/preferences
```

例如：

```json
{
  "preferred_locale": "zh-CN"
}
```

登录后用户切换语言：

```text
Vue
↓
立即切换 UI
↓
LocalStorage
↓
PATCH preferred_locale
↓
PostgreSQL
```

下次换电脑登录后仍然可以恢复用户语言。

---

# 十一、HTTP 请求语言

Axios 统一增加：

```http
Accept-Language: ja-JP
```

根据当前语言动态修改：

```text
zh-CN
ja-JP
en-US
```

不要每一个 API 自己添加。

统一在 Axios interceptor 中处理。

---

# 十二、后端语言处理

FastAPI 增加统一 Locale 解析。

顺序：

```text
1. 已登录用户 preferred_locale
2. Accept-Language
3. 系统 DEFAULT_LOCALE
```

统一 Locale 类型：

```python
SupportedLocale = Literal[
    "zh-CN",
    "ja-JP",
    "en-US"
]
```

不允许任意字符串进入系统。

---

# 十三、后端错误设计

不要让前端主要依赖后端返回的中文错误文字进行逻辑判断。

错误必须包含稳定：

```text
error_code
```

例如：

```json
{
  "success": false,
  "error_code": "MODEL_NOT_SUPPORT_IMAGE_TO_VIDEO",
  "message": "该模型不支持图生视频"
}
```

日语：

```json
{
  "success": false,
  "error_code": "MODEL_NOT_SUPPORT_IMAGE_TO_VIDEO",
  "message": "このモデルは画像からの動画生成に対応していません"
}
```

英语：

```json
{
  "success": false,
  "error_code": "MODEL_NOT_SUPPORT_IMAGE_TO_VIDEO",
  "message": "This model does not support image-to-video generation"
}
```

永远保持：

```text
error_code
```

不变。

---

# 十四、推荐的错误国际化策略

对于系统内已知错误：

前端优先根据：

```text
error_code
```

映射 i18n。

例如：

```text
errors.MODEL_DISABLED
errors.MODEL_NOT_SUPPORT_TEXT_TO_VIDEO
errors.MODEL_NOT_SUPPORT_IMAGE_TO_VIDEO
errors.INVALID_DURATION
errors.INVALID_RESOLUTION
errors.PUBLISH_ACCOUNT_DISABLED
errors.ACCESS_TOKEN_EXPIRED
errors.PERMISSION_DENIED
```

后端 `message` 作为：

```text
fallback
日志
动态错误说明
```

这样可以避免后端和前端翻译大量重复。

---

# 十五、第三方 API 错误

第三方模型和平台可能返回英文错误，例如：

```text
Invalid access token
Rate limit exceeded
```

不要直接原样展示给普通用户。

Adapter / Service 应转换成系统错误码：

```text
THIRD_PARTY_AUTH_FAILED
THIRD_PARTY_RATE_LIMITED
THIRD_PARTY_TIMEOUT
THIRD_PARTY_SERVICE_UNAVAILABLE
```

前端再翻译成：

中文：

```text
第三方服务认证失败
请求过于频繁，请稍后重试
```

日语：

```text
外部サービスの認証に失敗しました
リクエストが多すぎます。しばらくしてから再試行してください
```

英语：

```text
Third-party service authentication failed
Too many requests. Please try again later.
```

管理员日志可以保留详细第三方原始错误。

---

# 十六、状态翻译

数据库统一保存英文状态代码。

例如：

```text
pending
processing
success
failed
cancelled
timeout
publishing
```

语言文件：

```text
status.pending
status.processing
status.success
status.failed
status.cancelled
status.timeout
status.publishing
```

不要在数据库保存翻译后的状态。

---

# 十七、角色翻译

数据库保存：

```text
admin
user
```

前端显示：

中文：

```text
管理员
普通用户
```

日语：

```text
管理者
一般ユーザー
```

英语：

```text
Administrator
User
```

---

# 十八、模型名称处理

厂商和正式模型名称原则上不翻译。

例如：

```text
Google Veo 3.1
Runway Gen-4.5
Seedance 2.5
Luma Ray 3.2
MiniMax Hailuo 2.3
```

保持原名。

但模型的说明文字可以支持多语言。

如有必要，`video_models` 可以增加：

```text
description_i18n JSONB
```

例如：

```json
{
  "zh-CN": "支持文生视频和图生视频",
  "ja-JP": "テキスト・画像からの動画生成に対応",
  "en-US": "Supports text-to-video and image-to-video"
}
```

第一阶段不是必须字段。

---

# 十九、发布平台名称

品牌名称保持原名：

```text
X
Instagram
YouTube
Facebook
```

不要翻译品牌。

功能说明、配置说明和状态使用 i18n。

---

# 二十、管理员自定义内容

对于管理员自行输入的数据，例如：

```text
模型显示名称
模型备注
发布账号名称
内部备注
```

第一阶段不要求自动翻译。

用户输入什么就保存什么。

不要自动调用 LLM 翻译管理员输入内容。

---

# 二十一、用户 Prompt 不自动翻译

这是重要规则。

用户输入：

```text
东京夜晚的街道，下着小雨
```

系统应该原样发送给当前视频模型：

```text
东京夜晚的街道，下着小雨
```

不要因为 UI 当前语言为：

```text
ja-JP
```

就自动把 Prompt 翻译成日语。

UI 语言和生成内容语言是两个独立概念。

如果未来增加：

```text
Prompt 自动翻译
```

必须作为单独功能实现。

---

# 二十二、日期和时间国际化

统一保存：

```text
UTC
```

数据库不要保存格式化后的：

```text
2026年9月10日
```

前端根据 Locale 和时区显示。

推荐：

```typescript
Intl.DateTimeFormat
```

例如：

中文：

```text
2026/09/10 13:30
```

日语：

```text
2026/09/10 13:30
```

英语：

```text
Sep 10, 2026, 1:30 PM
```

如果系统面向日本企业：

默认时区可配置：

```text
Asia/Tokyo
```

时区与语言必须分开配置。

---

# 二十三、数字和文件大小

使用：

```typescript
Intl.NumberFormat
```

例如：

```text
1,000
1,234.56
```

文件大小建议统一使用：

```text
KB
MB
GB
```

不要在各页面重复实现格式化方法。

---

# 二十四、Element Plus 国际化

Element Plus 组件语言必须跟随当前系统语言。

包括：

- Pagination
- DatePicker
- TimePicker
- Calendar
- Table 空状态
- Upload
- Popconfirm

需要加载对应 Element Plus Locale：

```text
zh-cn
ja
en
```

用户切换语言时 Element Plus 也必须同步切换。

---

# 二十五、表单校验国际化

禁止写：

```typescript
message: '请输入用户名'
```

应写：

```typescript
message: t('validation.usernameRequired')
```

包括：

- 必填
- 最小长度
- 最大长度
- 文件大小
- 文件格式
- URL
- 邮箱
- 密码
- 模型参数
- 发布参数

都必须支持三语言。

---

# 二十六、确认框国际化

例如删除视频：

中文：

```text
确定要删除这个视频吗？
```

日语：

```text
この動画を削除しますか？
```

英语：

```text
Are you sure you want to delete this video?
```

按钮：

```text
确认 / キャンセル / Cancel
```

也必须国际化。

---

# 二十七、路由

URL 不随语言变化。

保持：

```text
/video/create
/videos
/publish/history
/admin/users
```

不要变成：

```text
/zh-CN/videos
/ja-JP/videos
```

这是内部管理系统，不需要 SEO 型多语言 URL。

---

# 二十八、语言切换组件

建议建立公共组件：

```text
LanguageSwitcher.vue
```

可以放在：

```text
登录页右上角
系统 Header
```

组件只负责：

- 当前语言
- 切换语言
- 保存偏好

不要在每个页面重复实现。

---

# 二十九、Fallback

任何翻译 Key 缺失时：

建议：

```text
当前语言
↓
en-US
↓
显示 key 并记录开发警告
```

或者：

```text
当前语言
↓
系统 DEFAULT_LOCALE
```

选择一种策略后全项目统一。

不能出现页面完全空白。

---

# 三十、翻译完整性检查

开发阶段增加检查。

确保：

```text
zh-CN
ja-JP
en-US
```

三个语言文件拥有相同的 Key 集合。

如果：

```text
zh-CN 有 500 个 key
ja-JP 只有 450 个
```

构建或测试应该尽量能发现。

可以写简单 Node / TypeScript 脚本检查。

---

# 三十一、前端测试

至少验证：

### 中文

```text
切换 zh-CN
↓
菜单
页面
按钮
表单
状态
错误
```

全部中文。

### 日语

```text
切换 ja-JP
```

不得残留大量中文。

### 英语

```text
切换 en-US
```

不得残留中文 / 日语。

---

# 三十二、后端测试

pytest 至少增加：

```text
preferred_locale 保存
preferred_locale 修改
非法 locale 拒绝
Accept-Language 解析
```

以及：

```text
zh-CN
ja-JP
en-US
```

基本错误消息处理。

---

# 三十三、联调测试

`03_全项目联调测试_Codex提示词.md` 中增加以下验收：

- [ ] 登录页可以切换中文
- [ ] 登录页可以切换日语
- [ ] 登录页可以切换英语
- [ ] 登录后语言偏好正确恢复
- [ ] 用户修改语言后数据库正确保存
- [ ] Vue 菜单全部切换
- [ ] Element Plus 组件同步切换
- [ ] 表单验证同步切换
- [ ] 视频生成状态同步切换
- [ ] 发布状态同步切换
- [ ] 管理后台同步切换
- [ ] 错误提示同步切换
- [ ] 三种语言不存在明显缺失 Key
- [ ] 页面刷新后语言保持
- [ ] 重新登录后语言保持

---

# 三十四、前端目录最终建议

```text
frontend/src/
├── api/
├── components/
│   └── LanguageSwitcher.vue
├── locales/
│   ├── index.ts
│   ├── zh-CN/
│   ├── ja-JP/
│   └── en-US/
├── router/
├── stores/
├── types/
├── utils/
└── views/
```

---

# 三十五、推荐数据库调整

`users`：

```text
id
username
...
preferred_locale
...
```

如果未来需要系统级默认语言配置，可以增加：

```text
system_settings
```

但第一阶段不是必须。

可以先通过：

```text
DEFAULT_LOCALE
```

环境变量管理。

---

# 三十六、最终开发原则

整个多语言系统遵循：

```text
数据库保存稳定代码
↓
API 返回稳定业务字段
↓
Vue 根据 locale 翻译
```

禁止：

```text
数据库保存中文状态
数据库保存日文角色
业务逻辑判断显示文字
```

必须：

```text
pending
admin
youtube
text_to_video
```

作为稳定内部值。

显示层再转换：

```text
待处理 / 処理待ち / Pending

管理员 / 管理者 / Administrator
```

最终必须做到：

**业务逻辑与语言完全解耦。**
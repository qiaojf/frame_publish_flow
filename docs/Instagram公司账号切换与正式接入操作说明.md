# Instagram 公司账号切换与正式接入操作说明

> 目的：将当前 PoC 阶段使用的个人开发者账号、个人/测试 Instagram 账号和 Access Token，全部替换为公司管理的账号与凭证。  
> 当前接入方式：Instagram API with Instagram Login  
> 主要用途：Instagram Reel 视频自动发布  
> 日期：2026-09-24

---

## 1. 最终目标

切换完成后，系统中的 Instagram 发布链路应全部使用公司资产：

```text
公司管理的 Meta Developer 管理员
        ↓
公司管理的 Meta App
        ↓
公司 Instagram Professional Account
        ↓
公司账号授权生成的 Access Token
        ↓
获取公司 Instagram ig_user_id
        ↓
配置到现有发布系统
        ↓
InstagramPublishAdapter
        ↓
创建 Container → 等待 FINISHED → media_publish
```

切换完成后，原个人账号原则上不再作为生产环境依赖。

---

## 2. 公司需要提前准备的内容

### 2.1 Meta Developer 管理人员

至少准备 1～2 名公司内部人员作为 Meta App 管理员。

建议：

- 使用公司员工本人长期管理的 Meta / Facebook 账号。
- 账号必须能够登录 Meta for Developers。
- 建议开启双重验证（2FA）。
- 不建议多人共用一个账号密码。
- 最好至少保留 2 名管理员，避免某一员工离职后无法管理 App。

需要准备：

```text
管理员姓名
管理员 Meta/Facebook 登录账号
管理员公司邮箱
是否已经注册 Meta for Developers
```

---

### 2.2 公司 Instagram 账号

准备一个公司实际使用或专门用于系统发布的 Instagram 账号。

要求：

```text
必须是 Professional Account
```

即：

```text
Business
或
Creator
```

不要使用普通 Personal Account。

需要准备：

```text
Instagram 用户名
Instagram 登录账号
Instagram 登录密码
可以接收登录验证的邮箱/手机
双重验证方式（如已开启）
```

本次使用 Instagram Login 方案，不要求为了 API 专门绑定 Facebook Page。

---

### 2.3 Meta App

公司需要拥有一个用于 Instagram API 的 Meta App。

建议两种处理方案：

#### 方案 A：公司重新创建一个新的 Meta App（推荐）

优点：

- 与个人 PoC App 完全分离。
- App ID / App Secret 从一开始就是公司管理。
- 后续 App Review、正式上线、人员权限管理更清晰。
- 不依赖原个人开发者账号。

适合当前情况，因为现阶段只是 PoC，迁移成本很低。

#### 方案 B：继续使用现有 PoC App

操作思路：

```text
先把公司人员加入现有 App
→ 赋予管理员权限
→ 确认公司管理员可以完整管理
→ 再逐步移除个人账号依赖
```

如果未来还涉及公司 Business Portfolio、Business Verification 或正式 App Review，需要再确认该 App 的组织归属是否符合公司管理要求。

本说明优先按 **方案 A：公司重新创建 App** 编写。

---

## 3. 需要保存的最终配置值

切换完成后需要得到以下参数。

### 3.1 平台配置

建议放在系统的“Instagram 平台配置”：

```text
client_id
client_secret
api_version
base_url
```

对应：

```text
client_id     = Meta App ID
client_secret = Meta App Secret
api_version   = 当前实际使用的 Graph API 版本
base_url      = https://graph.instagram.com
```

示例：

```json
{
  "client_id": "公司Meta App ID",
  "client_secret": "公司Meta App Secret",
  "api_version": "v26.0",
  "base_url": "https://graph.instagram.com"
}
```

注意：

```text
Client ID / App ID ≠ ig_user_id
```

---

### 3.2 账号配置

建议放在系统的“Instagram 账号配置”：

```text
username
ig_user_id
access_token
token_expires_at
```

示例：

```json
{
  "username": "company_instagram",
  "ig_user_id": "1784xxxxxxxxxxxx",
  "access_token": "IGAAxxxxxxxxxxxx",
  "token_expires_at": "2026-xx-xxTxx:xx:xx+09:00"
}
```

其中：

```text
ig_user_id
```

来自：

```http
GET https://graph.instagram.com/{api_version}/me
```

返回的：

```json
{
  "id": "...",
  "username": "...",
  "account_type": "BUSINESS"
}
```

这里的 `id` 才是 `ig_user_id`。

---

## 4. 公司侧具体操作步骤

# Step 1：准备公司 Meta Developer 管理员

公司指定管理员登录：

```text
https://developers.facebook.com/
```

如果尚未注册开发者：

```text
登录公司指定人员的 Meta/Facebook 账号
→ 注册 Meta for Developers
→ 完成开发者账号初始化
```

建议完成：

```text
邮箱验证
手机验证
双重验证（2FA）
```

至少准备两名公司管理员更安全。

---

# Step 2：创建公司 Meta App

进入：

```text
Meta for Developers
→ My Apps
→ Create App
```

创建新的公司 App。

建议继续使用与当前 PoC 相同的 Instagram API 接入方式：

```text
Instagram API with Instagram Login
```

添加/启用与 Instagram 内容管理和发布相关的 Use Case。

当前视频发布至少需要：

```text
instagram_business_basic
instagram_business_content_publish
```

目前不需要：

```text
instagram_business_manage_messages
instagram_business_manage_comments
```

除非以后要开发私信或评论功能。

---

# Step 3：记录公司 App ID 和 App Secret

进入 App：

```text
App Settings
→ Basic
```

记录：

```text
App ID
App Secret
```

系统对应关系：

```text
App ID     → 平台配置 client_id
App Secret → 平台配置 client_secret
```

注意：

- App Secret 只能保存在后端。
- 不要写入 Vue 前端。
- 不要提交到 GitHub。
- 不要在日志中打印。
- 不要通过聊天、邮件明文长期传播。

---

# Step 4：添加公司 Instagram 测试账号

在公司 Meta App 中进入 Instagram API 配置。

将公司的 Instagram Professional Account 添加为测试账号 / Tester。

如果页面要求添加 Instagram Tester：

```text
Meta Developer
→ App
→ App Roles / Instagram Tester
→ 添加公司 Instagram 用户名
```

添加后，该 Instagram 账号通常会处于：

```text
waiting for approval
```

状态。

---

# Step 5：公司 Instagram 账号接受 Tester 邀请

使用公司的 Instagram 账号登录 Instagram。

进入类似：

```text
Settings
→ Apps and Websites / Website Permissions
→ Tester Invites
```

找到公司 Meta App 发出的邀请。

点击：

```text
Accept
```

然后返回 Meta Developer 页面刷新。

确认该账号不再显示：

```text
waiting for approval
```

---

# Step 6：生成公司 Instagram Access Token

在公司 App 下，用公司 Instagram 账号完成授权。

授权时必须确认：

```text
当前登录的是公司 Instagram 账号
```

不是原 PoC 测试账号。

授权至少包含：

```text
instagram_business_basic
instagram_business_content_publish
```

生成后立即安全保存：

```text
ACCESS_TOKEN
```

不要继续使用原个人测试账号生成的 Token。

---

# Step 7：验证 Token 和取得公司 ig_user_id

执行：

```bash
curl "https://graph.instagram.com/v26.0/me?fields=id,username,account_type&access_token=公司ACCESS_TOKEN"
```

期望 HTTP：

```text
200
```

返回示例：

```json
{
  "id": "1784xxxxxxxxxxxx",
  "username": "company_instagram",
  "account_type": "BUSINESS"
}
```

记录：

```text
id = 公司 ig_user_id
```

同时确认：

```text
username = 公司 Instagram 用户名
account_type = BUSINESS 或 CREATOR
```

如果这里返回的用户名仍然是原测试账号，说明授权时登录错了 Instagram 账号，必须重新生成 Token。

---

# Step 8：确认 Token 权限

确认 Token 至少具备：

```text
instagram_business_basic
instagram_business_content_publish
```

可以使用 Meta Access Token Debugger 检查 Token 状态及有效期。

重点确认：

```text
Is Valid
Expires At
Scopes / Permissions
```

---

# Step 9：使用长效 Token

正式运行时不要长期依赖短效 Token。

如果当前得到的是可交换的短效 Instagram Token，可按 Meta 当前 Instagram Login Token 流程交换成长效 Token。

示例：

```bash
curl "https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=公司APP_SECRET&access_token=短效TOKEN"
```

成功时会返回类似：

```json
{
  "access_token": "IGAA...",
  "token_type": "bearer",
  "expires_in": 5184000
}
```

系统应保存：

```text
access_token
expires_in
token_expires_at
```

其中：

```text
token_expires_at = 当前时间 + expires_in
```

不要让管理员手工随意设置 Token 过期日期。

---

# Step 10：把公司参数配置到现有系统

## 平台配置

填写：

```text
Client ID      = 公司 Meta App ID
Client Secret  = 公司 Meta App Secret
API Version    = 当前实际使用版本
Base URL       = https://graph.instagram.com
```

---

## 账号配置

填写：

```text
Username       = 公司 Instagram 用户名
ig_user_id     = /me 返回的 id
Access Token   = 公司账号 Access Token
Token Expires  = Meta 返回/Debugger 显示的过期时间
```

注意：

```text
ig_user_id 和 access_token 属于账号配置
```

不要把 `ig_user_id` 填进 `Client ID`。

---

# Step 11：先测试 /me

更新系统配置后，先不要立即发布视频。

先验证：

```http
GET /me
```

确认系统使用的新配置返回的是：

```text
公司 Instagram username
公司 ig_user_id
```

如果仍然返回旧账号：

```text
说明系统仍在读取旧 Token / 旧账号配置
```

必须先排查缓存、数据库、环境变量或旧配置。

---

# Step 12：进行一次公司账号视频发布测试

使用一个公开 HTTPS 视频：

```text
https://.../test.mp4
```

执行当前系统已经实现的发布流程：

```text
POST /{ig_user_id}/media
        ↓
返回 container_id
        ↓
查询 container 状态
        ↓
FINISHED
        ↓
POST /{ig_user_id}/media_publish
        ↓
返回 media_id
```

最终确认：

```text
公司 Instagram 账号实际出现 Reel
```

如果发布成功，则公司账号切换完成。

---

## 5. 切换完成后的检查清单

正式完成切换前逐项确认：

- [ ] 公司人员可以登录 Meta for Developers。
- [ ] 至少一名公司人员拥有 App 管理权限。
- [ ] 最好存在第二名备用管理员。
- [ ] 使用的是公司 Meta App。
- [ ] App ID 已记录。
- [ ] App Secret 已安全保存。
- [ ] 公司 Instagram 账号是 Business 或 Creator。
- [ ] 公司 Instagram 账号已接受 Tester 邀请。
- [ ] Token 是由公司 Instagram 账号授权产生。
- [ ] Token 具有 `instagram_business_basic`。
- [ ] Token 具有 `instagram_business_content_publish`。
- [ ] `/me` 返回公司 Instagram 用户名。
- [ ] `/me` 返回的 `id` 已配置为 `ig_user_id`。
- [ ] Access Token 已配置到公司账号配置。
- [ ] Token 有效期已记录。
- [ ] 系统日志不会打印完整 Token。
- [ ] 视频 Container 可以创建成功。
- [ ] Container 可以到达 `FINISHED`。
- [ ] `media_publish` 可以返回 `media_id`。
- [ ] 公司 Instagram 实际出现测试 Reel。
- [ ] 原个人 Access Token 已从系统配置删除。
- [ ] 原个人 `ig_user_id` 已从系统配置删除。
- [ ] 原个人测试 Instagram 账号不再作为生产依赖。

---

## 6. 推荐的公司配置结构

### Instagram 平台配置

```json
{
  "platform": "instagram",
  "client_id": "<META_APP_ID>",
  "client_secret": "<META_APP_SECRET>",
  "base_url": "https://graph.instagram.com",
  "api_version": "v26.0",
  "poll_interval_seconds": 5,
  "processing_timeout_seconds": 300
}
```

---

### Instagram 账号配置

```json
{
  "platform": "instagram",
  "username": "<COMPANY_INSTAGRAM_USERNAME>",
  "ig_user_id": "<IG_USER_ID>",
  "access_token": "<ACCESS_TOKEN>",
  "token_expires_at": "<DATETIME>"
}
```

原则：

```text
平台配置 = App / API 公共参数
账号配置 = Instagram 账号身份和 Token
```

---

## 7. 原 PoC 账号和凭证如何处理

公司账号完整验证成功后，再处理原 PoC 配置。

建议顺序：

```text
先配置公司账号
→ /me 验证成功
→ 视频发布成功
→ 确认公司账号可独立运行
→ 再删除旧 Token
→ 再移除旧测试账号
→ 最后根据实际情况移除个人 App 管理权限
```

不要在公司配置验证成功之前先删除旧配置，以便出现问题时可以快速对比。

---

## 8. Access Token 运维要求

公司正式运行后，需要建立 Token 生命周期管理。

建议系统保存：

```text
access_token
token_expires_at
last_token_refresh_at
```

后续可增加：

```text
距离过期 7～10 天
→ 自动刷新 Token
→ 更新 access_token
→ 更新 token_expires_at
```

如果自动刷新失败：

```text
通知管理员
→ 禁止静默等待到 Token 彻底失效
```

---

## 9. 安全要求

以下内容属于敏感配置：

```text
App Secret
Access Token
Instagram 登录密码
2FA 恢复码
```

禁止：

```text
提交到 GitHub
写进前端代码
写入普通日志
放在公开文档
通过截图公开
```

建议：

```text
只存后端
数据库加密或 Secret Manager
日志脱敏
限制管理员查看权限
```

---

## 10. 当前阶段不需要立即处理的内容

如果现在仍然只是内部技术验证 / PoC，公司切换后仍可先不处理：

```text
App Review
Advanced Access
Business Verification
公司官网
Privacy Policy
正式 OAuth 登录页面
第三方客户 Instagram 授权
Webhook
评论管理
私信管理
```

这些可以等：

```text
公司账号自动发布流程稳定跑通
```

以后再做。

---

## 11. 如果未来要让客户连接自己的 Instagram

当前流程是：

```text
公司自己的 Instagram
→ 公司自己的 Token
→ 系统自动发布
```

如果以后变成：

```text
客户 A 登录自己的 Instagram
客户 B 登录自己的 Instagram
客户 C 登录自己的 Instagram
```

则需要进一步实施：

```text
Instagram Business Login / OAuth
App Review
所需权限的正式访问级别
Redirect URI
Token 生命周期管理
多账号隔离
隐私政策
数据删除机制
```

这属于下一阶段，不应与当前“公司账号替换”混在一起实施。

---

## 12. 建议的实际迁移顺序

建议严格按以下顺序执行：

```text
1. 确定公司 Meta 管理员
2. 创建公司 Meta App
3. 记录 App ID / App Secret
4. 确认公司 Instagram 为 Professional Account
5. 将公司 Instagram 加入 Tester
6. 公司 Instagram 接受邀请
7. 生成公司 Access Token
8. 用 /me 验证
9. 取得公司 ig_user_id
10. 检查 Token 权限和有效期
11. 必要时转换成长效 Token
12. 更新平台配置
13. 更新账号配置
14. 重启/重新加载后端配置
15. 再次调用 /me 确认已切换到公司账号
16. 发布一个测试 Reel
17. 确认公司 Instagram 实际收到 Reel
18. 删除系统中的旧个人 Token
19. 删除旧个人 ig_user_id
20. 最后再决定是否移除原个人 App 权限
```

---

## 13. 本次迁移完成标准

满足下面四项即可认为“公司化替换”完成：

```text
公司 Meta App
+
公司 Instagram Professional Account
+
公司账号生成的有效 Access Token
+
公司 ig_user_id
```

并且：

```text
/media
→ Container FINISHED
→ /media_publish
→ 公司 Instagram 出现 Reel
```

整个流程不再依赖原个人账号，即完成切换。

---

## 14. 官方参考

Meta 官方 Instagram API Postman Workspace：

https://www.postman.com/meta/instagram/overview

Instagram API：

https://www.postman.com/meta/instagram/collection/6yqw8pt/instagram-api

Instagram API with Instagram Login：

https://www.postman.com/meta/instagram/folder/1z5vxzu/instagram-api-with-instagram-login

当前 Instagram Login 发布所需主要权限：

```text
instagram_business_basic
instagram_business_content_publish
```

旧的：

```text
business_basic
business_content_publish
```

已经弃用，新接入不要继续使用。

# FrameFlow 前端

AI 视频制作与多平台发布平台的 Vue 3 前端。项目只通过统一 API Client 访问 FastAPI，不直连 AI 模型厂商或第三方发布平台，也不包含业务 Mock 数据。

## 环境要求

- Node.js 20.19+ 或 22.12+
- npm 10+
- FastAPI 服务（开发环境默认 `http://127.0.0.1:8000`）

## 启动

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

访问 `http://localhost:5173`。Vite 会把 `/api` 和 `/storage` 代理到 `VITE_DEV_PROXY_TARGET`。

## 验证与构建

```bash
npm run typecheck
npm run build
npm run preview
```

构建产物位于 `frontend/dist/`。

## 运行配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api/v1` | 后端 API 前缀 |
| `VITE_REQUEST_TIMEOUT_MS` | `20000` | 请求超时毫秒数 |
| `VITE_POLL_INTERVAL_MS` | `4000` | 生成、发布任务轮询间隔 |
| `VITE_MAX_IMAGE_SIZE_MB` | `10` | 后端未提供模型限制时的图片大小配置 |
| `VITE_DEV_PROXY_TARGET` | `http://127.0.0.1:8000` | 本地开发代理目标 |

## 联调约定

- 登录后 JWT 保存到浏览器本地存储，并由 Axios 请求拦截器自动注入。
- 401 会清理登录态并返回登录页；403 会显示统一权限提示。
- 模型能力、平台字段和发布账号均以后端返回数据为准。
- 后端未就绪时页面会显示真实错误或空状态，不会用前端假数据代替。
- Secret 查询只接受脱敏值；编辑时空值表示保持原配置，具体语义由后端确认。

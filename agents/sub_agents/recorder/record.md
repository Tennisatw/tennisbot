# Tennisatw 记录（待补全）

## 基本信息/偏好（待补全）
- 语言：中文
- 互动风格：偏轻松随聊

## 已知对话事实（按时间）
- 正在开发 Tennisbot
- 对多 agent / 工具能力有兴趣，常会切换到 developer 做调试。

## 待追问
- 你现在开发 Tennisbot 的核心目标是啥？
- 你希望“developer / recorder / 主 agent”各自的职责边界怎么划？
- 你希望 recorder 记录到什么粒度？
- 你对“记忆”的容忍度：宁可少记不误记，还是宁可多记再清理？
- 你希望我主要记录哪些：情绪/事件/目标/习惯/项目进度？

## 2026-01-06 记录（项目/技术）
- 用户（Tennisatw）在局域网 IP 访问 WebUI（`http://10.0.0.31:5173/`）时遇到 CORS + `localhost` 指向问题；本机 `127.0.0.1:5173` 正常。
- 代码层面问题点：前端 `web/frontend/src/App.svelte` 写死 `API_BASE = 'http://localhost:8000'`；后端 FastAPI CORS 仅允许 `localhost/127.0.0.1`。
- 已给出/落地修复方案（developer 已改代码）：
  - 前端改为同源相对路径：`API_BASE = ''`，请求 `/api/...`
  - WebSocket 改为同源：`${wsProto}://${location.host}/ws?...`
  - Vite dev server 增加 proxy：`/api` -> `http://127.0.0.1:8000`，`/ws` -> `ws://127.0.0.1:8000`
  - 后端 CORS allow_origins 追加 `http://10.0.0.31:5173` 作为兜底
- 用户倾向：不太能描述清楚后端部署/监听细节，更希望“直接读代码定位”。

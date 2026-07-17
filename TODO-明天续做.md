# 工作进度与明日计划

> 最近更新：2026-07-16 下午

---

## 一、当前状态总览

| 项目 | 状态 | 地址 / 说明 |
|------|------|-------------|
| GitHub 仓库 | ✅ 已建、已推送 | https://github.com/just706/knowledgegraph-ai |
| GitHub Pages（纯前端静态） | ✅ 已上线 | https://just706.github.io/knowledgegraph-ai/ |
| 本机 Docker 全功能（前后端） | ✅ 运行中 | backend:8000 healthy、frontend:5173 nginx |
| 公网访问（Cloudflare Tunnel） | ✅ 已打通、固定域名、手机可达 | https://kg.studykg.me/ |

### 固定域名（已生效）
```
https://kg.studykg.me/
```
- ✅ 前端 200、后端 `/api/v1/health` 200，全功能可用（2026-07-16 验证）。
- ✅ 手机移动网络可正常访问。
- ✅ 域名固定，关机/隧道退出后只要重新运行脚本就会恢复同一个域名。
- ✅ 2026-07-17 对齐网关统一入口：隧道由旧 `127.0.0.1:5173`（仅 PC）改为 `127.0.0.1:80`（网关），手机访问自动 UA 分发到移动端（含图谱可视化），PC 访问 PC 端。
- ⚠️ 仍需保持本机开机 + Docker 容器 + 本机代理 `127.0.0.1:7897` 运行。

### 命名隧道配置文件
- `C:\cloudflared\config.yml`
- `C:\cloudflared\start_tunnel.ps1`

### 启动/重启命令
```powershell
# 1) 确认 Docker 在跑、代理(127.0.0.1:7897)在跑
# 2) 运行：
powershell -ExecutionPolicy Bypass -File "C:\cloudflared\start_tunnel.ps1"
# 3) 验证域名：
Invoke-WebRequest -Uri "https://kg.studykg.me/" -UseBasicParsing
Invoke-WebRequest -Uri "https://kg.studykg.me/api/v1/health" -UseBasicParsing
```

---

## 二、今天（2026-07-16）完成的工作

- [x] 注册并登录 Cloudflare 账号（GitHub 登录）。
- [x] 购买域名 `studykg.me`。
- [x] 将 `studykg.me` 域名从阿里云 DNS 托管到 Cloudflare（NS 改为 `mallory.ns.cloudflare.com` + `nash.ns.cloudflare.com`）。
- [x] 创建 Cloudflare 命名隧道（Named Tunnel）`studykg`。
- [x] 创建 CNAME 记录 `kg.studykg.me` 指向命名隧道。
- [x] 编写 `C:\cloudflared\config.yml` 和启动脚本，绑定本机前端 `127.0.0.1:5173`。
- [x] 验证固定域名 `https://kg.studykg.me/` 与 API 全功能访问 200。
- [x] 2026-07-17：隧道入口改为网关 `127.0.0.1:80`，PC/移动端经 UA 自动分发；网关 `gateway.conf` 增强超时（180s）+ `docker-compose.yml` 修复 healthcheck（wget→sh -c 回退 curl，消除 unhealthy 误报）。

---

## 三、遗留 / 待办

### 1. 开机自启（可选）
将 `C:\cloudflared\start_tunnel.ps1` 配置为 Windows 开机自动启动，或注册为 Windows 服务，避免每次手动启动。需要时再做。

### 2. 云服务器部署（可选）
若要让服务完全脱离本机运行，需要购买一台带公网 IP 的云服务器部署后端，GitHub Pages 托管前端，并修改前端 API 基地址。

---

## 四、重要提醒

- **GitHub Pages 只托管前端静态页**，登录/问答/上传等后端功能在 Pages 上不可用；全功能目前依赖本机 Docker + Cloudflare Tunnel。
- 当前固定域名已永久可用，但服务仍在你的本机，需保持本机开机与相关进程运行。
- 如需分享给他人的固定链接：`https://kg.studykg.me/`

---

## 五、2026-07-17 修复：手机端无法登录/注册

### 现象
手机浏览器打开 `kg.studykg.me` 能看页面，但登录/注册后立刻被弹回登录页（登录"无效"）。

### 根因
后端 `CORS_ORIGINS` 白名单**未包含公网域名 `https://kg.studykg.me`**。
- 登录接口（`/users/login`，无 Authorization）本身不被 CORS 拦截 → 能拿到 token。
- 但 `auth.login()` 成功后会立即调用 `fetchUser()`（`GET /users/me`，带 `Bearer` token）。
  浏览器带 `Origin: https://kg.studykg.me` 请求，FastAPI CORSMiddleware 因 Origin 不在白名单而**不回显 `Access-Control-Allow-Origin`** → 浏览器拦截该响应 → axios 报错 → `App.vue` 的 catch 执行 `auth.logout()` → token 被清 → 回到登录页。
- 注册同理（register 后自动 login → fetchUser 失败 → 登出）。

### 修复
1. `backend/.env` 的 `CORS_ORIGINS` 增加 `https://kg.studykg.me`、`https://www.kg.studykg.me` 及移动端本地调试地址 `5174`。
2. 同步修改 `backend/app/config.py` 默认值（代码层兜底，防止 .env 被清空时遗漏）。
3. `docker compose up -d backend` 重启后端生效（无需 rebuild 镜像，因改动在 .env/配置层）。

### 验证
- 容器内 `python` 直接请求确认响应头 `Access-Control-Allow-Origin: https://kg.studykg.me` 已回显。
- 公网模拟手机 UA：`/users/login` → 200 拿 token；带 token 请求 `/users/me` → 200，完整登录流程打通。
- PC 端不受影响（原本就能登录，因同源 localhost 在白名单）。

### 2026-07-17 补充：打开即体验（自动登录体验账户）
- 需求：用户打开移动端即可直接体验，无需手动登录；个人中心展示账户信息。
- 实现：
  - `frontend-mobile/src/store/auth.ts` 新增 `ensureSession()`：已有合法会话则补充用户信息；否则以体验账户 `1234567@qq.com` / `admin` 静默登录（不弹 toast，失败不影响浏览）。`isLoggedIn` getter 改为 `token && user` 双重判定，避免"有 token 无 user"的悬空态。
  - `main.ts` 在 `app.mount()` 前 `await auth.ensureSession()`，保证首屏路由守卫已具备会话，不会被弹到登录页。
  - `ProfileView.vue` 增加"切换/登录我的账号"入口与体验账户说明文字。
- 验证：移动端镜像重建成功（top-level await 构建通过）；公网首页 200；`ensureSession` 与体验账户已编译进 `auth-*.js`；体验账户 login + `/users/me` 在服务端均 200（CORS 已修复）。


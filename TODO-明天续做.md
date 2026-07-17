# 工作进度与明日计划

> 最近更新：2026-07-17 下午

---

## 一、当前状态总览

| 项目 | 状态 | 地址 / 说明 |
|------|------|-------------|
| GitHub 仓库 | ✅ 已建、已推送 | https://github.com/just706/knowledgegraph-ai |
| GitHub Pages（纯前端静态） | ✅ 已上线 | https://just706.github.io/knowledgegraph-ai/ |
| 本机 Docker 全功能（前后端） | ✅ 运行中 | backend:8000 healthy、frontend:5173 nginx |
| 公网访问（Cloudflare Tunnel） | ✅ 已打通、固定域名、手机可达 | https://kg.studykg.me/ |
| 移动端 Vant 组件白屏 | ✅ 已修复 | 接入 unplugin-vue-components 按需导入 |
| 公网 CORS 登录 | ✅ 已修复 | 白名单已包含 kg.studykg.me |
| 移动端自动体验登录 | ✅ 已实现 | 打开即用，无需手动登录 |

### 固定域名（已生效）
```
https://kg.studykg.me/
```
- ✅ 前端 200、后端 `/api/v1/health` 200，全功能可用。
- ✅ 手机移动网络可正常访问。
- ✅ 域名固定，关机/隧道退出后只要重新运行脚本就会恢复同一个域名。
- ✅ 网关统一入口 UA 分发，手机自动走移动端、PC 走 PC 端。
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

## 二、今天（2026-07-17）完成的工作

### 1. 移动端 Vant 组件白屏修复 ⭐ 核心
- **问题**：手机打开 `kg.studykg.me` 只显示底部 tab 文字，中间内容区空白。
- **根因**：Vant 组件（`van-nav-bar`、`van-empty`、`van-field`、`van-button` 等）没有被注册/按需导入，浏览器无法渲染自定义标签。
- **修复**：
  - `vite.config.ts` 接入 `unplugin-vue-components` + `VantResolver`，实现组件自动按需导入。
  - `ChatView.vue` 增加原生 HTML 兜底状态（加载中/失败/重试），确保即使组件异常也能看到内容。
  - `ProfileView.vue` 增加原生 HTML 登录入口和状态显示。
  - `App.vue` 添加底部调试浮条，显示路由路径和登录状态，便于远程排查。
  - `index.html` 标题改为"AI学习助手"。
  - `gateway.conf` 添加 `Cache-Control: no-cache` + `Access-Control-Allow-Origin: *`，防止 Cloudflare/微信缓存旧版本，防止 iOS 跨域拒绝脚本执行。
- **验证**：重新构建并部署移动端容器，公网访问返回最新 HTML/JS。

### 2. 公网 CORS 登录修复
- 后端 `CORS_ORIGINS` 白名单新增 `https://kg.studykg.me`、`https://www.kg.studykg.me`。
- 修复登录/注册后因 `/users/me` CORS 拦截导致 token 被清 → 弹回登录页的问题。

### 3. 移动端自动体验登录
- `auth.ts` 新增 `ensureSession()`：启动时自动以体验账户静默登录。
- 用户打开即可使用全部功能，无需手动登录。

### 4. 网关增强
- 隧道入口改为 `127.0.0.1:80`（统一网关），PC/移动端经 UA 自动分发。
- 网关增加超时配置（180s）和 CORS/Cache-Control 头。
- `docker-compose.yml` 修复 healthcheck（wget→curl），消除 unhealthy 误报。

---

## 三、遗留 / 待办

### 1. ⚠️ 需手机端验证
- 移动端 Vant 组件修复后，需在**真实手机**上强制刷新验证：
  - 微信内：下拉页面松手刷新，或右上角菜单 → 刷新
  - 浏览器：清除缓存后重新打开 `https://kg.studykg.me/`
- 观察项：首页是否显示"AI助手"导航栏 + 聊天输入框；个人中心是否有"登录我的账号"入口。

### 2. Git Push（网络问题待重试）
- 本地 commit `79ccc41` 已创建，因网络连接重置 push 失败，需网络恢复后 `git push`。

### 3. 开机自启（可选）
将 `C:\cloudflared\start_tunnel.ps1` 配置为 Windows 开机自动启动，或注册为 Windows 服务。

### 4. 云服务器部署（可选）
若要让服务完全脱离本机运行，需要购买云服务器部署。

---

## 四、明日（2026-07-18）计划

### P0 - 验证与修复
- [ ] **手机端真机验证**：在真实手机上确认 Vant 白屏问题已解决，首页聊天功能正常
- [ ] **Git Push**：将本地 commit 推送到 GitHub
- [ ] 如有新 bug 根据手机截图定位修复

### P1 - 功能完善
- [ ] **知识图谱手机端体验优化**：检查图谱在手机端的交互是否流畅，必要时调整触控/缩放
- [ ] **学习中心数据对接**：检查移动端学习统计页数据是否正确显示
- [ ] **练习/测验功能验证**：在手机上走通答题→提交→查看结果的完整流程

### P2 - 体验打磨
- [ ] 移动端各页面 loading/空态/错误态统一检查
- [ ] 移动端响应式细节调整（字体大小、间距、安全区适配）
- [ ] PWA 离线缓存基础配置（Service Worker，可选）

### P3 - 文档与部署
- [ ] 更新 README.md 添加移动端使用说明
- [ ] 整理项目结构文档，方便后续维护

---

## 五、重要提醒

- **GitHub Pages 只托管前端静态页**，登录/问答/上传等后端功能在 Pages 上不可用；全功能目前依赖本机 Docker + Cloudflare Tunnel。
- 当前固定域名已永久可用，但服务仍在你的本机，需保持本机开机与相关进程运行。
- 如需分享给他人的固定链接：`https://kg.studykg.me/`


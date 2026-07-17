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


# 工作进度与明日计划

> 最近更新：2026-07-15 晚

---

## 一、当前状态总览

| 项目 | 状态 | 地址 / 说明 |
|------|------|-------------|
| GitHub 仓库 | ✅ 已建、已推送 | https://github.com/just706/knowledgegraph-ai |
| GitHub Pages（纯前端静态） | ✅ 已上线（HTTP 200） | https://just706.github.io/knowledgegraph-ai/ |
| 本机 Docker 全功能（前后端） | ✅ 运行中 | backend:8000 healthy、frontend:5173 nginx |
| 公网访问（Cloudflare Tunnel） | ✅ 已打通、手机可达 | 见下方临时域名 |

### Cloudflare Tunnel 公网地址（临时）
```
https://loc-mate-remember-allied.trycloudflare.com/
```
- ✅ 前端 200、后端 /api/v1/health 200，全功能可用。
- ✅ 已实测：手机移动网络（非局域网）可正常访问。
- ⚠️ **临时域名**：电脑关机 / 隧道进程退出即失效，重启后域名会变。
- ⚠️ 依赖本机开机 + cloudflared 进程 + Docker 容器均在运行。

---

## 二、今天（2026-07-15）完成的工作

- [x] 核对任务列表，确认仓库已建、已推送、Pages 已上线（旧 TODO 已过时）。
- [x] 验证 GitHub Pages 站点可正常访问（HTTP 200）。
- [x] 安装 cloudflared v2026.7.1，用 quick tunnel 将本机前端(5173) 暴露到公网。
- [x] 排查并修复隧道 403 问题：
  - 定位根因为 **Vite allowedHosts Host 校验**（外部域名被拒）。
  - `frontend/vite.config.ts` 新增 `allowedHosts: true`。
  - `frontend/nginx.conf` 将 API 代理 Host 固定为 `backend:8000`，避免外部域名透传触发 Host/CORS 校验。
  - 重建前端镜像后，隧道域名返回 200，API 同样 200。
- [x] 验证公网全链路：前端页面 + 后端 API 均可用。
- [x] 验证手机移动网络（脱离局域网）可访问，网络可达确认通过。

---

## 三、遗留 / 待办（明日优先）

### 1. 提交并推送本次改动（优先级：高）
当前工作区有未提交改动，需 commit + push：
- `frontend/vite.config.ts`（allowedHosts:true）
- `frontend/nginx.conf`（API 代理 Host 固定）
- 之前 Docker 相关未提交文件：`backend/Dockerfile`、`backend/app/config.py`、`backend/requirements.txt`、`docker-compose.yml`、`frontend/Dockerfile`
- 新增：`backend/pytest.ini`

```powershell
cd "D:\KnowledgeGraph AI 智能学习助手系统"
git add -A
git commit -m "feat: 修复 Cloudflare Tunnel 公网访问(Vite allowedHosts + nginx 代理 Host)"
git push
```

### 2. 固定公网域名（优先级：中，可选）
临时域名重启即变，若要长期稳定对外分享，建议其一：
- **方案 A（推荐）**：Cloudflare 命名隧道（Named Tunnel）
  - 需要：Cloudflare 账号 + 一个自有域名（或用 Cloudflare 免费域名策略）。
  - 步骤：`cloudflared tunnel login` → `tunnel create` → 配 `config.yml` 绑定域名 → `tunnel run`。
  - 好处：域名固定，可配开机自启为 Windows 服务，别人链接永久有效。
- **方案 B**：部署后端到有公网 IP 的服务器 + Pages 配 `VITE_API_BASE_URL`，实现纯云端全功能（不依赖本机开机）。

### 3. 让隧道随开机自启（优先级：低，视需求）
- 将 cloudflared 注册为 Windows 服务，避免每次手动开隧道。
- 需在完成"固定域名"后再做，临时隧道自启意义不大（域名仍会变）。

---

## 四、重要提醒

- **GitHub Pages 只托管前端静态页**，登录/问答/上传等后端功能在 Pages 上不可用；全功能目前依赖本机 Docker + Cloudflare Tunnel。
- 若要真正"不依赖本机开机"的全功能公网服务，必须走上面的 **方案 B**（云服务器部署后端）。
- 分享临时链接给他人试用时，务必保持本机开机、隧道与容器进程存活。

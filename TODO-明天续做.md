# 待办：GitHub 发布（明天续做）

> 当前状态（2026-07-14 晚）：所有代码改动已 commit 到本地 `master` 分支，工作区干净。
> 卡点：本机网络访问 github.com 超时（443 连不上），`gh auth login` 失败，远程仓库尚未创建、代码尚未推送。

## 明天步骤

### 1. 解决网络（关键前提）
在 PowerShell 测试能否连通：
```powershell
Test-NetConnection github.com -Port 443
```
- 若 `TcpTestSucceeded=False`：开启 VPN/代理，或换手机热点，然后给 git 配代理（端口按你代理实际值改）：
```powershell
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

### 2. 登录 GitHub（用 token，跳过浏览器授权页）
1. 浏览器登录 GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)
2. 勾选：`repo`、`workflow`、`read:org`，生成并复制 token（ghp_ 开头，自己保存，别外传）
3. PowerShell 执行（token 自己粘贴）：
```powershell
$env:GH_TOKEN = "<你的token>"
gh auth login --with-token
```

### 3. 一键发布
```powershell
cd "D:\KnowledgeGraph AI 智能学习助手系统"
powershell -ExecutionPolicy Bypass -File .\deploy-to-github.ps1 -Repo knowledgegraph-ai
```
脚本会：建仓库 → 推送 master → 启用 GitHub Pages。
完成后站点：https://<你的用户名>.github.io/knowledgegraph-ai/

### 4. 验证
- 打开 Actions 页看 `deploy-pages` 工作流是否绿
- 访问上面的 Pages 地址，确认前端页面能打开

## 重要提醒
- **GitHub Pages 只能托管前端静态页**，登录/问答/上传等需要后端 API 的功能暂时不可用。
- 要让功能真正可用：把后端用之前配好的 Docker 部署到有公网 IP 的服务器，拿到 `https://api.你的域名.com`，
  然后在仓库 **Settings → Secrets and variables → Actions → Variables** 新增：
  `VITE_API_BASE_URL = https://api.你的域名.com/api/v1`，再重跑一次 Pages 工作流。

## 已完成清单（本次会话）
- [x] 后端 Dockerfile + 前端 Dockerfile + nginx.conf + docker-compose.yml
- [x] 根 .env.example（修正硬编码 SECRET_KEY）
- [x] 后端/前端/.dockerignore
- [x] CI 工作流 ci.yml + docker-publish.yml（推 GHCR）
- [x] PRD §1.12 部署与运维 + 第八章容器化说明
- [x] README 进度/目录结构同步
- [x] 前端适配 Pages：hash 路由、Vite base、favicon 相对路径
- [x] Pages 部署工作流 deploy-pages.yml
- [x] .gitignore 补全（.env / *.bak / 缓存 / 停止追踪日志）
- [x] gh CLI 已通过 winget 安装（v2.96.0）
- [x] 一键发布脚本 deploy-to-github.ps1
- [x] 所有改动已 commit 到本地 master

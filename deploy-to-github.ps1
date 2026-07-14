# ============================================================
# 一键发布到 GitHub 并启用 Pages（仅前端静态站点）
# 使用前提：已执行 gh auth login 完成登录
# 用法（在项目根目录）：
#   powershell -ExecutionPolicy Bypass -File .\deploy-to-github.ps1 -Repo knowledgegraph-ai
# 参数：
#   -Repo     仓库名（默认 knowledgegraph-ai）
#   -Private  加此开关则创建私有仓库（默认公开，Pages 免费需公开或 Pro）
# ============================================================
param(
    [string]$Repo = "knowledgegraph-ai",
    [switch]$Private
)

$ErrorActionPreference = "Stop"

# 定位 gh（新装后当前会话可能未刷新 PATH）
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) { $gh = "C:\Program Files\GitHub CLI\gh.exe" }
if (-not (Test-Path $gh)) { throw "找不到 gh CLI，请先安装：winget install --id GitHub.cli" }

Write-Host "==> 检查登录状态..." -ForegroundColor Cyan
& $gh auth status
if ($LASTEXITCODE -ne 0) { throw "未登录，请先执行： gh auth login" }

# 当前登录用户名
$user = (& $gh api user --jq ".login").Trim()
Write-Host "==> 当前用户：$user，目标仓库：$user/$Repo" -ForegroundColor Cyan

$vis = if ($Private) { "--private" } else { "--public" }

# 创建远程仓库（若已存在则跳过创建，仅设置 remote）
Write-Host "==> 创建 GitHub 仓库..." -ForegroundColor Cyan
& $gh repo create "$Repo" $vis --source "." --remote origin --push
if ($LASTEXITCODE -ne 0) {
    Write-Host "仓库可能已存在，尝试直接推送到现有 origin..." -ForegroundColor Yellow
    git remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0) {
        git remote add origin "https://github.com/$user/$Repo.git"
    }
    git push -u origin HEAD
}

# 启用 GitHub Pages（Source = GitHub Actions）
Write-Host "==> 启用 GitHub Pages (build_type=workflow)..." -ForegroundColor Cyan
& $gh api -X POST "repos/$user/$Repo/pages" -f "build_type=workflow" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $gh api -X PUT "repos/$user/$Repo/pages" -f "build_type=workflow" 2>$null
}

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Green
Write-Host " 推送完成！GitHub Actions 将自动构建并部署前端。" -ForegroundColor Green
Write-Host " 站点地址： https://$user.github.io/$Repo/" -ForegroundColor Green
Write-Host ""
Write-Host " 后续（重要）：" -ForegroundColor Yellow
Write-Host " 1) 部署好后端后，在仓库 Settings -> Secrets and variables -> Actions -> Variables"
Write-Host "    新增变量 VITE_API_BASE_URL = https://你的后端域名/api/v1"
Write-Host "    然后重跑 Deploy Frontend to GitHub Pages 工作流。"
Write-Host " 2) 查看部署进度： https://github.com/$user/$Repo/actions"
Write-Host "===========================================================" -ForegroundColor Green

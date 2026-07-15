# ============================================================
# One-click publish to GitHub and enable Pages (frontend static site)
# Prerequisite: gh auth login done
# Usage (in project root):
#   powershell -ExecutionPolicy Bypass -File .\deploy-to-github.ps1 -Repo knowledgegraph-ai
# Params:
#   -Repo     repository name (default knowledgegraph-ai)
#   -Private  create a private repo (default public; Pages free needs public or Pro)
# ============================================================
param(
    [string]$Repo = "knowledgegraph-ai",
    [switch]$Private
)

$ErrorActionPreference = "Stop"

# Locate gh (PATH may not be refreshed right after install)
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) { $gh = "C:\Program Files\GitHub CLI\gh.exe" }
if (-not (Test-Path $gh)) { throw "gh CLI not found. Install: winget install --id GitHub.cli" }

Write-Host "==> Checking auth status..." -ForegroundColor Cyan
& $gh auth status
if ($LASTEXITCODE -ne 0) { throw "Not logged in. Run: gh auth login" }

# Current login name
$user = (& $gh api user --jq ".login").Trim()
Write-Host "==> User: $user  Target repo: $user/$Repo" -ForegroundColor Cyan

$vis = if ($Private) { "--private" } else { "--public" }

# Create remote repo (if exists, skip create and just set remote/push)
Write-Host "==> Creating GitHub repo..." -ForegroundColor Cyan
& $gh repo create "$Repo" $vis --source "." --remote origin --push
if ($LASTEXITCODE -ne 0) {
    Write-Host "Repo may already exist, trying to push to existing origin..." -ForegroundColor Yellow
    git remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0) {
        git remote add origin "https://github.com/$user/$Repo.git"
    }
    git push -u origin HEAD
}

# Enable GitHub Pages (Source = GitHub Actions)
Write-Host "==> Enabling GitHub Pages (build_type=workflow)..." -ForegroundColor Cyan
& $gh api -X POST "repos/$user/$Repo/pages" -f "build_type=workflow" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $gh api -X PUT "repos/$user/$Repo/pages" -f "build_type=workflow" 2>$null
}

Write-Host ""
Write-Host "===========================================================" -ForegroundColor Green
Write-Host " Push done. GitHub Actions will build and deploy the frontend." -ForegroundColor Green
Write-Host " Site URL: https://$user.github.io/$Repo/" -ForegroundColor Green
Write-Host ""
Write-Host " Next (important):" -ForegroundColor Yellow
Write-Host " 1) After deploying backend, go to repo Settings -> Secrets and variables -> Actions -> Variables"
Write-Host "    Add variable VITE_API_BASE_URL = https://your-backend-domain/api/v1"
Write-Host "    Then re-run the 'Deploy Frontend to GitHub Pages' workflow."
Write-Host " 2) Actions progress: https://github.com/$user/$Repo/actions"
Write-Host "===========================================================" -ForegroundColor Green

# Deployment script for Cloudflare Pages
# Usage: .\scripts\deploy.ps1

Write-Host "🚀 Deploying Baselinr Demo to Cloudflare Pages..." -ForegroundColor Cyan

# Check if wrangler is installed
if (-not (Get-Command wrangler -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Error: wrangler CLI not found. Install it with: npm install -g wrangler" -ForegroundColor Red
    exit 1
}

# Navigate to frontend directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $scriptPath ".."
Set-Location $frontendDir

Write-Host "📦 Building frontend for demo mode..." -ForegroundColor Yellow
npm run build:demo

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed! Fix errors before deploying." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "out")) {
    Write-Host "❌ Error: Build output directory 'out' not found!" -ForegroundColor Red
    exit 1
}

Write-Host "☁️  Deploying to Cloudflare Pages..." -ForegroundColor Yellow
wrangler pages deploy out --project-name=baselinr-demo

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    Write-Host "🌐 Your demo should be available at: https://baselinr-demo.pages.dev" -ForegroundColor Cyan
} else {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    exit 1
}

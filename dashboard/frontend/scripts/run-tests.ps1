# Frontend test runner script for git hooks (PowerShell)
# Runs Vitest tests and exits with appropriate code

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $scriptDir ".."

Set-Location $frontendDir

Write-Host "Running frontend tests..." -ForegroundColor Cyan

try {
    npm run test:run
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Frontend tests passed" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "[FAIL] Frontend tests failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Frontend tests failed: $_" -ForegroundColor Red
    exit 1
}


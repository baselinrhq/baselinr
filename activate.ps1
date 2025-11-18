# Quick activation script for Baselinr virtual environment
# Usage: .\activate.ps1

Write-Host "Activating Baselinr virtual environment..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1
Write-Host "Virtual environment activated!" -ForegroundColor Green
Write-Host ""
Write-Host "Quick commands:" -ForegroundColor Cyan
Write-Host "  baselinr --help" -ForegroundColor White
Write-Host "  baselinr plan --config examples/config.yml" -ForegroundColor White
Write-Host "  pytest tests/ -v" -ForegroundColor White
Write-Host ""
Write-Host "To deactivate: deactivate" -ForegroundColor Yellow


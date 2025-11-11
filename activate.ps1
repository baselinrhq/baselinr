# Quick activation script for ProfileMesh virtual environment
# Usage: .\activate.ps1

Write-Host "Activating ProfileMesh virtual environment..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1
Write-Host "Virtual environment activated!" -ForegroundColor Green
Write-Host ""
Write-Host "Quick commands:" -ForegroundColor Cyan
Write-Host "  profilemesh --help" -ForegroundColor White
Write-Host "  profilemesh plan --config examples/config.yml" -ForegroundColor White
Write-Host "  pytest tests/ -v" -ForegroundColor White
Write-Host ""
Write-Host "To deactivate: deactivate" -ForegroundColor Yellow


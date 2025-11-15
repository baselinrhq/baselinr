# Fix Node.js PATH for PowerShell
# Run this script as Administrator if needed

Write-Host "Checking Node.js installation..." -ForegroundColor Cyan

$nodePath = "C:\Program Files\nodejs"
$npmPath = "C:\Program Files\nodejs\npm.cmd"

if (Test-Path $nodePath) {
    Write-Host "Node.js found at: $nodePath" -ForegroundColor Green
    
    # Add to current session PATH
    $env:PATH += ";$nodePath"
    Write-Host "Added to current session PATH" -ForegroundColor Green
    
    # Verify
    Write-Host "`nVerifying installation..." -ForegroundColor Cyan
    $nodeVersion = & node --version 2>&1
    $npmVersion = & npm --version 2>&1
    
    if ($nodeVersion -match "v\d+") {
        Write-Host "✓ Node.js: $nodeVersion" -ForegroundColor Green
    } else {
        Write-Host "✗ Node.js not working" -ForegroundColor Red
    }
    
    if ($npmVersion -match "\d+\.\d+") {
        Write-Host "✓ npm: $npmVersion" -ForegroundColor Green
    } else {
        Write-Host "✗ npm not working" -ForegroundColor Red
    }
    
    Write-Host "`nNote: This fix is temporary for this session." -ForegroundColor Yellow
    Write-Host "To make it permanent:" -ForegroundColor Yellow
    Write-Host "1. Restart your terminal/IDE (recommended)" -ForegroundColor Yellow
    Write-Host "2. Or run this as Administrator to add to system PATH permanently" -ForegroundColor Yellow
    
} else {
    Write-Host "Node.js not found at expected location: $nodePath" -ForegroundColor Red
    Write-Host "Please check your Node.js installation." -ForegroundColor Red
}



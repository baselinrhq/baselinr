# Frontend Test Scripts

These scripts are used by git hooks to run frontend tests.

## Files

- `run-tests.sh` - Bash script for Linux/Mac
- `run-tests.ps1` - PowerShell script for Windows

## Usage in Git Hooks

### Pre-push Hook (Recommended)

Add to `.git/hooks/pre-push` (bash) or `.git/hooks/pre-push.ps1` (PowerShell):

**Bash version:**
```bash
# Run frontend tests
if [ -d "dashboard/frontend" ]; then
    echo "Running frontend tests..."
    bash dashboard/frontend/scripts/run-tests.sh || exit 1
fi
```

**PowerShell version:**
```powershell
# Run frontend tests
if (Test-Path "dashboard/frontend") {
    Write-Host "Running frontend tests..." -ForegroundColor Cyan
    & "dashboard/frontend/scripts/run-tests.ps1"
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
```

### Pre-commit Hook (Optional)

Frontend tests are fast (~2 seconds), so they could also be added to pre-commit if desired.
However, pre-push is recommended to keep pre-commit fast.

## Manual Execution

You can also run these scripts manually:

```bash
# Bash
bash dashboard/frontend/scripts/run-tests.sh

# PowerShell
powershell -ExecutionPolicy Bypass -File dashboard/frontend/scripts/run-tests.ps1
```


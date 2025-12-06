# Git Hooks

Baselinr uses git hooks to ensure code quality before commits and pushes.

## Available Hooks

### Pre-commit Hook (Fast Checks)

Runs automatically before each commit:
- **Code formatting** check with `black`
- **Linting** check with `flake8`
- **Import sorting** check with `isort`

**Time**: ~5-10 seconds

**Purpose**: Catch formatting and style issues quickly before committing.

### Pre-push Hook (Full Tests)

Runs automatically before pushing to remote:
- **Full test suite** with `pytest`
- **Frontend tests** with `vitest` (if dashboard/frontend exists)
- Excludes Dagster integration tests (known compatibility issues)

**Time**: ~30-60 seconds (Python tests) + ~2-5 seconds (frontend tests)

**Purpose**: Ensure all tests pass before code reaches the remote repository.

## Installation

Hooks are automatically installed when you clone the repository. If you need to reinstall:

```bash
make install-hooks
```

Or manually:

```bash
# Make hooks executable (Linux/Mac)
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

## Usage

### Normal Workflow

Hooks run automatically:
```bash
# Pre-commit runs automatically
git commit -m "Add feature"

# Pre-push runs automatically
git push
```

### Skipping Hooks

If you need to skip hooks (use sparingly):

```bash
# Skip pre-commit
git commit --no-verify -m "WIP: temporary commit"

# Skip pre-push
git push --no-verify
```

⚠️ **Warning**: Only skip hooks when absolutely necessary. Broken code should be fixed, not bypassed.

## Troubleshooting

### "Command not found" errors

**Problem**: Python or tools not found in hook.

**Solution**: Ensure virtual environment is activated or tools are installed:
```bash
# Install dev dependencies
make install-dev

# Or manually
pip install black flake8 isort pytest
```

### Hooks not running

**Problem**: Hooks not executing on Windows.

**Solution**: 
- On Windows, git may use PowerShell hooks (`.ps1` files)
- Ensure git is configured to use bash or PowerShell appropriately
- Check hook permissions: `ls -la .git/hooks/`

### Tests failing in pre-push

**Problem**: Tests fail but you want to push anyway.

**Solution**: 
1. **Fix the tests** (recommended)
2. Use `git push --no-verify` (not recommended for production code)

### Slow pre-commit

**Problem**: Pre-commit takes too long.

**Solution**: 
- Pre-commit should be fast (< 10 seconds)
- If it's slow, check if tools are installed correctly
- Consider running only on changed files (advanced)

## Customization

### Modify Hook Behavior

Edit the hook files directly:
- `.git/hooks/pre-commit` (bash/sh)
- `.git/hooks/pre-commit.ps1` (PowerShell)
- `.git/hooks/pre-push` (bash/sh)
- `.git/hooks/pre-push.ps1` (PowerShell)

### Add More Checks

Add to pre-commit hook:
```bash
# Example: Add mypy type checking
$PYTHON -m mypy baselinr/ || {
    echo "❌ Type checking failed!"
    exit 1
}
```

### Change Test Suite

Modify pre-push hook to run different tests:
```bash
# Run only specific tests
$PYTHON -m pytest tests/test_drift_strategies.py -v
```

### Add Frontend Tests

Frontend tests are automatically included if you add the test runner script to your pre-push hook.

**Bash version** (add to `.git/hooks/pre-push`):
```bash
# Run frontend tests
if [ -d "dashboard/frontend" ]; then
    echo "Running frontend tests..."
    bash dashboard/frontend/scripts/run-tests.sh || exit 1
fi
```

**PowerShell version** (add to `.git/hooks/pre-push.ps1`):
```powershell
# Run frontend tests
if (Test-Path "dashboard/frontend") {
    Write-Host "Running frontend tests..." -ForegroundColor Cyan
    & "dashboard/frontend/scripts/run-tests.ps1"
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
```

See `dashboard/frontend/scripts/README.md` for more details.

## Best Practices

1. **Fix issues, don't skip**: If hooks fail, fix the issue rather than using `--no-verify`
2. **Keep hooks fast**: Pre-commit should complete in < 10 seconds
3. **Test locally first**: Run `make test` before pushing
4. **Update hooks carefully**: Changes affect all developers

## See Also

- [Development Guide](DEVELOPMENT.md) - General development setup
- [Makefile](../../Makefile) - Available make commands
- [Git Hooks Documentation](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)


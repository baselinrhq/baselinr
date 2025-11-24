# Local Testing Guide for dbt Integration

This guide helps you test the dbt integration locally before pushing to CI.

## Prerequisites

1. PostgreSQL running (use docker-compose or your own instance)
2. dbt-core installed: `pip install dbt-core dbt-postgres`
3. baselinr installed in development mode: `pip install -e ..`

## Quick Test

1. **Set up test dbt project:**
   
   **On Linux/Mac:**
   ```bash
   cd dbt_package
   bash test_local.sh
   ```
   
   **On Windows (PowerShell):**
   ```powershell
   cd dbt_package
   .\test_local.ps1
   ```

2. **Start PostgreSQL** (if using docker-compose):
   ```bash
   cd ../docker
   docker compose up -d postgres
   ```

3. **Compile dbt project:**
   
   **On Linux/Mac:**
   ```bash
   cd /tmp/test_dbt_project_local
   export DBT_PROFILES_DIR=./profiles
   dbt compile --profiles-dir ./profiles
   ```
   
   **On Windows (PowerShell):**
   ```powershell
   cd $env:TEMP\test_dbt_project_local
   $env:DBT_PROFILES_DIR='.\profiles'
   dbt compile --profiles-dir .\profiles
   ```

4. **Run the test script:**
   
   **On Linux/Mac:**
   ```bash
   cd ../../baselinr/dbt_package
   python test_local.py /tmp/test_dbt_project_local/target/manifest.json
   ```
   
   **On Windows (PowerShell):**
   ```powershell
   cd ..\..\baselinr\dbt_package
   python test_local.py "$env:TEMP\test_dbt_project_local\target\manifest.json"
   ```

The test script will show you:
- All models found in the manifest
- Where tags are stored (tags vs config.tags)
- Results of tag queries
- Results of ref resolution

## Debugging Tag Issues

If tags aren't being found, the test script will show you the exact structure of each model node in the manifest. This helps identify where dbt is actually storing the tags.

## Manual Testing

You can also test interactively:

```python
from baselinr.integrations.dbt import DBTManifestParser
import json
import tempfile
import os

# Use appropriate temp path for your OS
if os.name == 'nt':  # Windows
    manifest_path = os.path.join(tempfile.gettempdir(), 'test_dbt_project_local', 'target', 'manifest.json')
else:
    manifest_path = '/tmp/test_dbt_project_local/target/manifest.json'

parser = DBTManifestParser(manifest_path=manifest_path)

# Check all models
all_models = parser.get_all_models()
for model in all_models:
    print(f"{model.get('name')}: tags={model.get('tags')}, config={model.get('config')}")

# Test tag lookup
models = parser.get_models_by_tag('critical')
print(f"Found {len(models)} models with 'critical' tag")
```


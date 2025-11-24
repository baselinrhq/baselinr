# Migration Guide: Monorepo to Separate Repository

This guide helps you migrate from using the dbt package from the main baselinr monorepo to the new standalone `dbt-baselinr` repository.

## What Changed

The dbt package has been moved from a subdirectory in the main baselinr repository to its own dedicated repository:

- **Old location**: `https://github.com/baselinrhq/baselinr/tree/main/dbt_package`
- **New location**: `https://github.com/baselinrhq/dbt-baselinr`

## Benefits of the New Structure

- **Independent versioning**: dbt package versions are independent of the main baselinr Python package
- **Faster installation**: Only downloads the dbt package, not the entire baselinr repository
- **Better discoverability**: Standalone repository is easier to find and contribute to
- **dbt Hub ready**: Structure is optimized for future dbt Hub publishing

## Migration Steps

### 1. Update `packages.yml`

**Before:**
```yaml
packages:
  - git: "https://github.com/baselinrhq/baselinr.git"
    subdirectory: dbt_package
```

**After:**
```yaml
packages:
  - git: "https://github.com/baselinrhq/dbt-baselinr.git"
    revision: v0.1.0  # or latest tag
```

### 2. Update Package Dependencies

Run the following command to update your dbt packages:

```bash
dbt deps
```

This will:
- Remove the old package from `dbt_packages/baselinr/`
- Install the new package from the standalone repository

### 3. Verify Installation

Check that the package is correctly installed:

```bash
# Verify package structure
ls dbt_packages/baselinr/

# Should show:
# - macros/
# - scripts/
# - tests/
# - dbt_project.yml
```

### 4. Test Your Models

Run a test to ensure everything still works:

```bash
# Compile your project
dbt compile

# Run a model with baselinr profiling
dbt run --select your_model_name

# Run baselinr drift tests
dbt test --select your_model_name
```

## No Code Changes Required

The package API remains the same. All macros (`baselinr_profile`, `baselinr_drift`, `baselinr_config`) work exactly as before. No changes are needed to your `schema.yml` files or model configurations.

## Version Compatibility

| dbt-baselinr | baselinr (Python) | Notes |
|--------------|------------------|-------|
| 0.1.x        | >=0.3.0          | Initial standalone release |

## Troubleshooting

### Package Not Found

If `dbt deps` fails, ensure:
- You have the correct repository URL
- The tag/revision exists (check [releases](https://github.com/baselinrhq/dbt-baselinr/releases))
- You have network access to GitHub

### Macros Not Found

If dbt can't find the macros:
1. Verify the package installed: `ls dbt_packages/baselinr/macros/`
2. Run `dbt clean` and then `dbt deps` again
3. Check your `dbt_project.yml` has the correct `packages-install-path`

### Script Path Issues

The script paths in macros use `dbt_packages/baselinr/scripts/`. If you have custom paths set via `baselinr_script_path` variable, update them if needed.

## Support

If you encounter issues during migration:

1. Check the [dbt-baselinr issues](https://github.com/baselinrhq/dbt-baselinr/issues)
2. Review the [documentation](https://github.com/baselinrhq/dbt-baselinr/blob/main/README.md)
3. Open a new issue with details about your setup

## Rollback

If you need to rollback to the monorepo version temporarily:

```yaml
packages:
  - git: "https://github.com/baselinrhq/baselinr.git"
    subdirectory: dbt_package
    revision: <commit-hash>  # Pin to a specific commit
```

**Note**: The monorepo version is deprecated and will not receive updates. Please migrate to the standalone repository.


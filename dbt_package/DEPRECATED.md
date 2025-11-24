# ⚠️ This Directory is Deprecated

**The dbt package has been moved to a separate repository.**

## New Location

👉 **[https://github.com/baselinrhq/dbt-baselinr](https://github.com/baselinrhq/dbt-baselinr)**

## Quick Migration

Update your `packages.yml`:

**Before (deprecated):**
```yaml
packages:
  - git: "https://github.com/baselinrhq/baselinr.git"
    subdirectory: dbt_package
```

**After (new):**
```yaml
packages:
  - git: "https://github.com/baselinrhq/dbt-baselinr.git"
    revision: v0.1.0
```

Then run:
```bash
dbt deps
```

## Why the Change?

- ✅ **Independent versioning**: dbt package versions are independent of the main baselinr Python package
- ✅ **Faster installation**: Only downloads the dbt package, not the entire baselinr repository
- ✅ **Better discoverability**: Standalone repository is easier to find and contribute to
- ✅ **dbt Hub ready**: Structure is optimized for future dbt Hub publishing
- ⚠️ **This directory will not receive updates**

## Migration Guide

See [MIGRATION.md](./MIGRATION.md) for detailed migration instructions.

## Questions?

- **New Repository**: https://github.com/baselinrhq/dbt-baselinr
- **Issues**: https://github.com/baselinrhq/dbt-baselinr/issues
- **Documentation**: See README.md in the new repository

---

**Last updated**: This directory is deprecated as of baselinr v0.3.0


# Rebrand Dashboard to Quality Studio and Update Footer

## Summary

This PR rebrands the dashboard terminology to "Quality Studio" throughout the codebase and documentation, emphasizing the no-code data quality setup capabilities. It also updates the sidebar footer to reflect the current year (2025) and version (v1.0).

## Changes Made

### Rebranding
- **Renamed "dashboard" to "Quality Studio"** across all documentation and user-facing text
- Updated main README to highlight the **no-code data quality setup UI** as a key feature
- Updated page title and metadata from "Baselinr Dashboard" to "Baselinr Quality Studio"
- Updated sidebar subtitle from "Data Quality Hub" to "Quality Studio"

### Documentation Updates
- **Main README.md**: Added comprehensive section about Quality Studio's no-code capabilities
- **docs/dashboard/README.md**: Updated to reflect Quality Studio branding and features
- **docs/schemas/UI_COMMAND.md**: Updated all references from "dashboard" to "Quality Studio"
- **docs/dashboard/QUICKSTART.md**: Updated quick start guide
- **docs/dashboard/ARCHITECTURE.md**: Updated architecture documentation
- **docs/dashboard/DASHBOARD_INTEGRATION.md**: Updated integration guide
- **docs/README.md**: Updated documentation index

### UI Updates
- **Sidebar Footer**: Updated copyright year from 2024 to 2025 and version from v2.0 to v1.0
- **Page Metadata**: Updated title and description to reflect Quality Studio branding

### Code Quality
- Fixed linting errors: removed unused imports (`Settings` from ConfigHub, `Badge` and `clsx` from RunsTable components)
- Fixed failing test: Updated `BaselineConfig.test.tsx` to use `getAllByText` for "prior period" field that appears multiple times

## Key Features Highlighted

The Quality Studio is now positioned as:
- **No-Code Configuration**: Complete web-based UI for setting up and managing data quality configuration
- **Visual Configuration Management**: Set up connections, storage, tables, profiling, validation rules, and drift detection through visual forms
- **Visual & YAML Editor**: Split-view editor with real-time sync between visual forms and YAML configuration
- **Monitoring & Analysis**: View profiling runs, drift alerts, validation results, and root cause analysis

## Testing

- ✅ All pre-commit checks passed (linting, formatting)
- ✅ All frontend tests passed (547 tests)
- ✅ All Python tests passed (829 tests)
- ✅ No linting errors or warnings

## Files Changed

- `README.md` - Main project README with Quality Studio feature highlights
- `dashboard/frontend/components/Sidebar.tsx` - Footer updates and branding
- `dashboard/frontend/app/layout.tsx` - Page metadata updates
- `docs/dashboard/*.md` - All dashboard documentation files
- `docs/schemas/UI_COMMAND.md` - UI command documentation
- `docs/README.md` - Documentation index
- Various component files - Linting fixes

## Checklist

- [x] Code follows project style guidelines
- [x] All tests pass
- [x] Documentation updated
- [x] No linting errors
- [x] Changes are backward compatible (directory structure unchanged, only terminology updated)

## Notes

- The `dashboard/` directory structure remains unchanged to avoid breaking changes
- All user-facing text and documentation now uses "Quality Studio" terminology
- The rebranding emphasizes the no-code setup capabilities as a key differentiator




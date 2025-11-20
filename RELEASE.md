# Release Guide

Quick reference guide for creating releases of Baselinr.

## Quick Start

1. **Tag and push**:
   ```bash
   git tag v0.1.1  # Use appropriate version (patch/minor/major)
   git push origin v0.1.1
   ```

2. **Wait for automation**: GitHub Actions will automatically:
   - Build the package
   - Publish to PyPI
   - Create a GitHub Release

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **PATCH** (`0.1.0` → `0.1.1`): Bug fixes, patches
- **MINOR** (`0.1.0` → `0.2.0`): New features (non-breaking)
- **MAJOR** (`0.1.0` → `1.0.0`): Breaking changes

## Release Checklist

Before creating a release tag:

- [ ] All tests pass: `make test`
- [ ] Code is formatted: `make format`
- [ ] Linting passes: `make lint`
- [ ] Documentation is up to date
- [ ] CHANGELOG updated (if maintained)
- [ ] Version number determined (patch/minor/major)

## Creating the Tag

```bash
# Patch release (bug fixes)
git tag v0.1.1
git push origin v0.1.1

# Minor release (new features)
git tag v0.2.0
git push origin v0.2.0

# Major release (breaking changes)
git tag v1.0.0
git push origin v1.0.0
```

## Verify Release

After pushing the tag, check:

1. **GitHub Actions**: https://github.com/baselinrhq/baselinr/actions
   - Look for "Release" workflow to complete successfully

2. **PyPI**: https://pypi.org/project/baselinr/
   - Verify new version appears
   - Test installation: `pip install baselinr==<version>`

3. **GitHub Releases**: https://github.com/baselinrhq/baselinr/releases
   - Verify release notes were created

## Troubleshooting

### Release workflow failed

- Check GitHub Actions logs for errors
- Verify PyPI trusted publishing is configured
- Ensure tag format matches `v*.*.*` (e.g., `v0.1.1`)

### Version not appearing on PyPI

- Check PyPI project settings → Trusted publishing
- Verify repository is linked: `baselinrhq/baselinr`
- Check GitHub Actions logs for PyPI publish step

### Version is wrong

- Ensure git tags exist: `git tag`
- Verify setuptools-scm is installed: `pip install setuptools-scm`
- Check tag format matches SemVer: `v0.1.1` not `0.1.1` (note the `v` prefix)

## Development Version

To check the current development version:

```bash
cd baselinr
python -c "from setuptools_scm import get_version; print(get_version())"
```

This will show something like `0.1.0.dev5+gabc123` if no release tag exists.

## Manual Release (If Needed)

If you need to manually publish:

```bash
# Install build tools
pip install build twine setuptools-scm

# Build package
python -m build

# Verify package
python -m twine check dist/*

# Publish to PyPI (requires credentials)
python -m twine upload dist/*
```

## Rapid Release Strategy

For rapid development with frequent releases:

- **Daily releases**: Use patch versions (`0.1.1`, `0.1.2`, `0.1.3`, ...)
- **Weekly feature releases**: Use minor versions (`0.2.0`, `0.3.0`, ...)
- **Major milestones**: Use major versions (`1.0.0`, `2.0.0`, ...)

You can release as frequently as needed - each tag triggers an automated release.


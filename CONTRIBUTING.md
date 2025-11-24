# Contributing to Baselinr

Thank you for your interest in contributing to Baselinr! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue using the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md). Include:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, database type)
- Relevant error messages or logs

### Suggesting Features

Feature requests are welcome! Please use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) and include:
- Clear description of the feature
- Use case and motivation
- Potential implementation approach (if you have ideas)

### Contributing Code

1. **Fork the repository**
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```
3. **Make your changes**
4. **Test your changes**:
   ```bash
   make test
   ```
5. **Ensure code quality**:
   ```bash
   make format
   make lint
   ```
6. **Commit your changes** with clear, descriptive messages
7. **Push to your fork** and open a Pull Request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- (Optional) Docker for running the development environment

### Setup Steps

1. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/baselinr.git
   cd baselinr
   ```

2. **Create a virtual environment**:
   ```bash
   make venv
   # Activate it:
   # Windows: .\activate.ps1
   # Linux/Mac: source .venv/bin/activate
   ```

3. **Install development dependencies**:
   ```bash
   make install-dev
   ```

4. **Install git hooks** (optional but recommended):
   ```bash
   make install-hooks
   ```

5. **Start development environment** (optional):
   ```bash
   make docker-up
   ```

## Development Workflow

### Code Style

We use:
- **Black** for code formatting (line length: 100)
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking (where applicable)

Run formatting and linting:
```bash
make format  # Formats code with black and isort
make lint    # Runs flake8 and mypy
```

### Testing

- Write tests for new features and bug fixes
- Ensure all tests pass: `make test`
- Aim for good test coverage
- Tests are located in the `tests/` directory

### Type Hints

- Add type hints to function signatures
- Use type hints for complex data structures
- We use Python 3.10+ type hint syntax

### Documentation

- Add docstrings to public functions and classes
- Update README.md if adding new features
- Update relevant docs in `docs/` directory
- Keep examples up to date

## Pull Request Process

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Ensure all checks pass**:
   - Tests pass
   - Code is formatted
   - Linters pass
   - CI checks pass

3. **Write a clear PR description**:
   - What changes were made
   - Why the changes were made
   - How to test the changes
   - Any breaking changes

4. **Link related issues** in the PR description

5. **Wait for review** - maintainers will review your PR

6. **Address feedback** - make requested changes and push updates

## Project Structure

```
baselinr/
├── baselinr/          # Main package
│   ├── config/        # Configuration management
│   ├── connectors/    # Database connectors
│   ├── profiling/     # Profiling engine
│   ├── drift/         # Drift detection
│   ├── storage/       # Results storage
│   └── ...
├── tests/             # Test suite
├── docs/              # Documentation
├── examples/             # Examples
└── ...
```

## Adding a New Database Connector

1. Create a new file in `baselinr/connectors/` (e.g., `newdb.py`)
2. Inherit from `BaseConnector` in `connectors/base.py`
3. Implement required methods
4. Add to `connectors/__init__.py`
5. Update `DatabaseType` enum in `config/schema.py`
6. Add tests in `tests/`
7. Update documentation

See `docs/development/DEVELOPMENT.md` for detailed examples.

## Adding a New Metric

1. Add metric calculation logic to `profiling/metrics.py`
2. Add metric name to configuration schema
3. Add tests
4. Update documentation

## Commit Message Guidelines

Write clear, descriptive commit messages:

```
feat: Add support for MySQL connector
fix: Handle null values in drift detection
docs: Update installation instructions
test: Add tests for incremental profiling
refactor: Simplify configuration loading
```

Use conventional commit prefixes:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `style:` - Code style changes (formatting)
- `chore:` - Maintenance tasks

## Release Process

Baselinr uses [Semantic Versioning](https://semver.org/) (SemVer) with automated releases via GitHub Actions and PyPI.

### Version Numbering

Versions follow the format `MAJOR.MINOR.PATCH`:

- **PATCH** (`0.1.0` → `0.1.1`): Bug fixes, patches, minor improvements
- **MINOR** (`0.1.0` → `0.2.0`): New features, enhancements (non-breaking)
- **MAJOR** (`0.1.0` → `1.0.0`): Breaking changes, major API changes

While in `0.x.y`, breaking changes may bump MINOR instead of MAJOR.

### Automated Versioning

Version numbers are automatically generated from git tags using `setuptools-scm`. The version is:
- Read from the latest git tag (e.g., `v0.1.0` → version `0.1.0`)
- Auto-generated for development installs (e.g., `0.1.0.dev5+gabc123`)
- Stored in `baselinr/baselinr/_version.py` (auto-generated, do not edit)

### Creating a Release

1. **Prepare your release**:
   - Ensure all tests pass: `make test`
   - Update CHANGELOG.md (if maintained) or review recent commits
   - Determine the appropriate version bump (patch/minor/major)

2. **Create and push a git tag**:
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

3. **Automated release process**:
   - GitHub Actions automatically:
     - Builds the package using the tag
     - Runs package verification checks
     - Publishes to PyPI (if trusted publishing is configured)
     - Creates a GitHub Release with release notes

4. **Verify the release**:
   - Check PyPI: https://pypi.org/project/baselinr/
   - Check GitHub Releases: https://github.com/baselinrhq/baselinr/releases
   - Test installation: `pip install baselinr==<version>`

### Release Workflow

The release process is fully automated via `.github/workflows/release.yml`:

- **Trigger**: Pushing a tag matching `v*.*.*` (e.g., `v0.1.1`)
- **Build**: Creates source distribution and wheel
- **Publish**: Uploads to PyPI using trusted publishing
- **Release**: Creates a GitHub Release with changelog

### PyPI Trusted Publishing Setup

To enable automated PyPI publishing:

1. Go to PyPI → Your project → Settings → Manage API tokens
2. Enable "Trusted publishing" for your GitHub repository
3. Add the repository: `baselinrhq/baselinr`
4. Save the configuration

Once enabled, releases will automatically publish to PyPI without requiring API tokens.

### Development Releases

For development/testing before a full release:

1. Create a pre-release tag: `v0.1.1-rc1` or `v0.2.0-alpha1`
2. These will be published to PyPI with the full tag as the version
3. Users can install with: `pip install baselinr==0.1.1rc1`

### Rapid Release Workflow

When pushing PRs rapidly:

- **Daily releases**: Use patch versions (`0.1.1`, `0.1.2`, `0.1.3`, ...)
- **Weekly feature releases**: Use minor versions (`0.2.0`, `0.3.0`, ...)
- **Major milestones**: Use major versions (`1.0.0`, `2.0.0`, ...)

You can release as frequently as needed - each tag triggers a new release automatically.

### Manual Release (if needed)

If you need to manually build and publish:

```bash
# Install build tools
pip install build twine setuptools-scm

# Build package
python -m build

# Verify package
python -m twine check dist/*

# Publish to PyPI (requires PyPI credentials)
python -m twine upload dist/*
```

## Questions?

- Check existing [issues](https://github.com/baselinrhq/baselinr/issues)
- Review [documentation](docs/)
- Open a discussion on GitHub

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0 (see LICENSE file).

---

Thank you for contributing to Baselinr! 🎉


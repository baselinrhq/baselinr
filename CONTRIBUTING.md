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

## Questions?

- Check existing [issues](https://github.com/baselinrhq/baselinr/issues)
- Review [documentation](docs/)
- Open a discussion on GitHub

## License

By contributing, you agree that your contributions will be licensed under the Business Source License 1.1 (see LICENSE file).

---

Thank you for contributing to Baselinr! 🎉


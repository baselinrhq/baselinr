# Baselinr Makefile
# Common development and deployment commands

.PHONY: help install install-dev install-all test lint format clean docker-up docker-down docker-logs venv activate install-hooks

help:
	@echo "Baselinr - Available Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make venv           Create Python 3.14 virtual environment"
	@echo "  make dev-setup      Create venv and install dev dependencies"
	@echo "  make activate       Show how to activate the virtual environment"
	@echo ""
	@echo "Installation (run after activating venv):"
	@echo "  make install        Install Baselinr"
	@echo "  make install-dev    Install with development dependencies"
	@echo "  make install-all    Install with all optional dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linters"
	@echo "  make format         Format code"
	@echo "  make clean          Clean build artifacts"
	@echo "  make install-hooks  Install git hooks (pre-commit & pre-push)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up           Start Docker environment (includes Prometheus & Grafana)"
	@echo "  make docker-down         Stop Docker environment"
	@echo "  make docker-down-volumes Stop and remove volumes"
	@echo "  make docker-rebuild      Full rebuild (down -v, build, up)"
	@echo "  make docker-logs         View Docker logs"
	@echo "  make docker-metrics      Start only Prometheus & Grafana services"
	@echo ""
	@echo "Usage:"
	@echo "  make quickstart     Run the quickstart example"
	@echo "  make profile        Profile tables (requires config)"
	@echo ""

venv:
	@echo "Creating Python 3.14 virtual environment..."
	py -3.14 -m venv .venv
	@echo ""
	@echo "Virtual environment created!"
	@echo "To activate: .\activate.ps1  (or .\.venv\Scripts\Activate.ps1)"
	@echo ""

dev-setup: venv
	@echo ""
	@echo "Installing development dependencies..."
	.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
	.venv\Scripts\python.exe -m pip install -e ".[dev]"
	@echo ""
	@echo "Installing git hooks..."
	@$(MAKE) install-hooks
	@echo ""
	@echo "========================================="
	@echo "Setup complete!"
	@echo "========================================="
	@echo ""
	@echo "To activate the virtual environment:"
	@echo "  .\activate.ps1"
	@echo ""
	@echo "Or manually:"
	@echo "  .\.venv\Scripts\Activate.ps1"
	@echo ""
	@echo "Git hooks installed! They will run automatically on commit/push."
	@echo ""

activate:
	@echo ""
	@echo "To activate the virtual environment, run:"
	@echo ""
	@echo "  .\activate.ps1"
	@echo ""
	@echo "Or manually:"
	@echo "  .\.venv\Scripts\Activate.ps1"
	@echo ""
	@echo "To deactivate when done:"
	@echo "  deactivate"
	@echo ""

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all,dev]"

test:
	pytest tests/ -v

lint:
	flake8 baselinr/ --config=.flake8
	mypy baselinr/

format:
	black baselinr/ examples/
	isort baselinr/ examples/

install-hooks:
	@echo "Installing git hooks..."
ifeq ($(OS),Windows_NT)
	@if not exist .git\hooks mkdir .git\hooks
	@if exist hooks\pre-commit copy /Y hooks\pre-commit .git\hooks\pre-commit >nul 2>&1 && echo ✅ Installed pre-commit hook || echo ⚠️  Warning: hooks\pre-commit not found
	@if exist hooks\pre-push copy /Y hooks\pre-push .git\hooks\pre-push >nul 2>&1 && echo ✅ Installed pre-push hook || echo ⚠️  Warning: hooks\pre-push not found
else
	@if [ ! -d ".git/hooks" ]; then \
		echo "Error: .git/hooks directory not found. Are you in a git repository?"; \
		exit 1; \
	fi
	@if [ -f "hooks/pre-commit" ]; then \
		cp hooks/pre-commit .git/hooks/pre-commit; \
		chmod +x .git/hooks/pre-commit; \
		echo "✅ Installed pre-commit hook"; \
	else \
		echo "⚠️  Warning: hooks/pre-commit not found"; \
	fi
	@if [ -f "hooks/pre-push" ]; then \
		cp hooks/pre-push .git/hooks/pre-push; \
		chmod +x .git/hooks/pre-push; \
		echo "✅ Installed pre-push hook"; \
	else \
		echo "⚠️  Warning: hooks/pre-push not found"; \
	fi
endif
	@echo ""
	@echo "Git hooks installed successfully!"
	@echo ""
	@echo "Pre-commit: Runs fast checks (formatting, linting)"
	@echo "Pre-push: Runs full test suite"
	@echo ""
	@echo "To skip hooks: git commit --no-verify or git push --no-verify"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/

docker-up:
	cd docker && docker compose up -d
	@echo ""
	@echo "Docker environment started!"
	@echo "Dagster UI: http://localhost:3000"
	@echo "Grafana: http://localhost:3001 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "PostgreSQL: localhost:5433 (user: baselinr, password: baselinr)"

docker-down:
	cd docker && docker compose down

docker-down-volumes:
	cd docker && docker compose down -v
	@echo ""
	@echo "Containers stopped and volumes removed"

docker-rebuild:
	@echo "Stopping containers and removing volumes..."
	cd docker && docker compose down -v
	@echo ""
	@echo "Rebuilding images..."
	cd docker && docker compose build
	@echo ""
	@echo "Starting containers..."
	cd docker && docker compose up -d
	@echo ""
	@echo "Docker environment rebuilt and started!"
	@echo "Dagster UI: http://localhost:3000"
	@echo "Grafana: http://localhost:3001 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "PostgreSQL: localhost:5433 (user: baselinr, password: baselinr)"

docker-logs:
	cd docker && docker compose logs -f

docker-metrics:
	cd docker && docker compose up -d prometheus grafana
	@echo ""
	@echo "Metrics services started!"
	@echo "Grafana: http://localhost:3001 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo ""
	@echo "Note: Make sure Baselinr is running with metrics enabled:"
	@echo "  baselinr profile --config examples/config.yml"

quickstart:
	python examples/quickstart.py

plan:
	baselinr plan --config examples/config.yml

profile:
	baselinr profile --config examples/config.yml

drift:
	baselinr drift --config examples/config.yml --dataset customers

# Full development environment (install + docker)
dev-env: install-dev docker-up
	@echo ""
	@echo "Development environment ready!"
	@echo "Run 'make quickstart' to test Baselinr"


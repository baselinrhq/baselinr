# ProfileMesh Makefile
# Common development and deployment commands

.PHONY: help install install-dev install-all test lint format clean docker-up docker-down docker-logs

help:
	@echo "ProfileMesh - Available Commands"
	@echo "================================="
	@echo ""
	@echo "Installation:"
	@echo "  make install        Install ProfileMesh"
	@echo "  make install-dev    Install with development dependencies"
	@echo "  make install-all    Install with all optional dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linters"
	@echo "  make format         Format code"
	@echo "  make clean          Clean build artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      Start Docker environment"
	@echo "  make docker-down    Stop Docker environment"
	@echo "  make docker-logs    View Docker logs"
	@echo ""
	@echo "Usage:"
	@echo "  make quickstart     Run the quickstart example"
	@echo "  make profile        Profile tables (requires config)"
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
	flake8 profilemesh/
	mypy profilemesh/

format:
	black profilemesh/ examples/
	isort profilemesh/ examples/

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
	cd docker && docker-compose up -d
	@echo ""
	@echo "Docker environment started!"
	@echo "Dagster UI: http://localhost:3000"
	@echo "PostgreSQL: localhost:5432 (user: profilemesh, password: profilemesh)"

docker-down:
	cd docker && docker-compose down

docker-logs:
	cd docker && docker-compose logs -f

quickstart:
	python examples/quickstart.py

plan:
	profilemesh plan --config examples/config.yml

profile:
	profilemesh profile --config examples/config.yml

drift:
	profilemesh drift --config examples/config.yml --dataset customers

# Development workflow
dev-setup: install-dev docker-up
	@echo ""
	@echo "Development environment ready!"
	@echo "Run 'make quickstart' to test ProfileMesh"


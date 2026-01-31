# Makefile for Binance AI Trader development

.PHONY: help install install-dev test lint format typecheck clean docs ci

# Default target
help:
	@echo "Binance AI Trader - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make install-dev      Install with development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test             Run tests"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo "  make lint             Run linter (ruff)"
	@echo "  make format           Format code"
	@echo "  make typecheck        Run type checker (mypy)"
	@echo "  make check            Run all checks (lint + typecheck)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove build artifacts and cache"
	@echo ""
	@echo "CI:"
	@echo "  make ci               Run all CI checks"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest tests/ app/tests/

test-coverage:
	pytest --cov=. --cov-report=html --cov-report=term-missing

test-unit:
	pytest -m unit tests/unit/

test-integration:
	pytest -m integration tests/integration/

# Code quality
lint:
	ruff check .

lint-fix:
	ruff check --fix .

format:
	ruff format .

typecheck:
	mypy .

check: lint typecheck
	@echo "✅ All checks passed"

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Documentation
docs:
	@echo "Documentation:"
	@echo "  README.md"
	@echo "  CONTRIBUTING.md"
	@echo "  ARCHITECTURAL_BOUNDARIES.md"

# CI pipeline
ci: clean lint typecheck test
	@echo "✅ CI pipeline completed successfully"

# Web UI
web:
	python -m interfaces.web.main --config config/config.yaml --host 127.0.0.1 --port 8000

# CLI
cli:
	python -m interfaces.cli.main

# Doctor check
doctor:
	python -m interfaces.cli.main doctor

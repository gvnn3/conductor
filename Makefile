# Makefile for Conductor development

# Python interpreter
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin

# Directories
SRC_DIR := conductor
TEST_DIR := tests
SCRIPTS_DIR := scripts
DOCS_DIR := .

# Test settings
PYTEST_OPTS := -v
COVERAGE_OPTS := --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: venv
venv: ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/pip install --upgrade pip setuptools wheel

.PHONY: install
install: venv ## Install conductor in development mode
	$(VENV_BIN)/pip install -e .
	$(VENV_BIN)/pip install pytest pytest-cov pytest-mock

.PHONY: install-dev
install-dev: install ## Install development dependencies
	$(VENV_BIN)/pip install ruff mypy hypothesis

.PHONY: clean
clean: ## Clean build artifacts and cache
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

.PHONY: test
test: ## Run all tests
	$(VENV_BIN)/pytest $(PYTEST_OPTS) $(TEST_DIR)

.PHONY: test-fast
test-fast: ## Run tests excluding slow integration tests
	$(VENV_BIN)/pytest $(PYTEST_OPTS) -m "not slow" $(TEST_DIR)

.PHONY: test-integration
test-integration: ## Run only integration tests
	$(VENV_BIN)/pytest $(PYTEST_OPTS) -m "slow" $(TEST_DIR)

.PHONY: test-cli
test-cli: ## Run CLI-specific tests
	$(VENV_BIN)/pytest $(PYTEST_OPTS) $(TEST_DIR)/test_conduct_cli.py $(TEST_DIR)/test_player_cli.py $(TEST_DIR)/test_cli_integration.py

.PHONY: test-file
test-file: ## Run specific test file (use TEST=filename)
	$(VENV_BIN)/pytest $(PYTEST_OPTS) $(TEST)

.PHONY: test-hypothesis
test-hypothesis: ## Run property-based tests with Hypothesis
	$(VENV_BIN)/pytest $(PYTEST_OPTS) $(TEST_DIR)/test_*hypothesis*.py $(TEST_DIR)/test_*edge_cases*.py

.PHONY: coverage
coverage: ## Run tests with coverage report
	$(VENV_BIN)/pytest $(COVERAGE_OPTS) $(TEST_DIR)

.PHONY: coverage-html
coverage-html: coverage ## Generate HTML coverage report
	@echo "Coverage report generated in htmlcov/index.html"
	@$(PYTHON) -m webbrowser htmlcov/index.html 2>/dev/null || true

.PHONY: lint
lint: ## Run code linting with ruff
	$(VENV_BIN)/ruff check $(SRC_DIR) $(TEST_DIR) $(SCRIPTS_DIR)

.PHONY: format
format: ## Format code with ruff
	$(VENV_BIN)/ruff format $(SRC_DIR) $(TEST_DIR) $(SCRIPTS_DIR)

.PHONY: typecheck
typecheck: ## Run type checking with mypy
	$(VENV_BIN)/mypy $(SRC_DIR) --ignore-missing-imports

.PHONY: audit
audit: ## Run test quality audit
	$(VENV_BIN)/pytest $(PYTEST_OPTS) $(TEST_DIR)/test_detailed_audit.py -s

.PHONY: demo-local
demo-local: ## Run localhost demo
	@echo "Starting player in background..."
	@$(VENV_BIN)/player tests/localhost/dut.cfg &
	@sleep 1
	@echo "Running conductor..."
	@$(VENV_BIN)/conduct tests/localhost/conductor.cfg
	@echo "Demo complete. Player still running - kill manually if needed."

.PHONY: demo-timeout
demo-timeout: ## Run timeout demo
	@echo "Starting player in background..."
	@$(VENV_BIN)/player tests/timeout/dut.cfg &
	@sleep 1
	@echo "Running conductor..."
	@$(VENV_BIN)/conduct tests/timeout/conductor.cfg
	@echo "Demo complete. Player still running - kill manually if needed."

.PHONY: docs
docs: ## Build documentation
	@echo "Building documentation..."
	@echo "Documentation is in Markdown format:"
	@echo "  - README.md"
	@echo "  - QUICK_START.md"
	@echo "  - INSTALLATION_GUIDE.md"
	@echo "  - CLI_REFERENCE.md"
	@echo "  - ARCHITECTURE.md"

.PHONY: check
check: lint typecheck test ## Run all checks (lint, typecheck, test)

.PHONY: check-fast
check-fast: lint test-fast ## Run fast checks (lint, fast tests)

.PHONY: build
build: clean ## Build distribution packages
	$(VENV_BIN)/pip install --upgrade pip build
	$(VENV_BIN)/python -m build

.PHONY: release
release: check build ## Prepare for release (run all checks and build)
	@echo "Release artifacts built in dist/"
	@echo "Don't forget to:"
	@echo "  1. Update version in pyproject.toml"
	@echo "  2. Update CHANGELOG"
	@echo "  3. Tag the release"
	@echo "  4. Push to PyPI if applicable"

# Development shortcuts
.PHONY: t
t: test-fast ## Shortcut for fast tests

.PHONY: tc
tc: test-cli ## Shortcut for CLI tests

.PHONY: c
c: coverage ## Shortcut for coverage

.PHONY: l
l: lint ## Shortcut for lint

.PHONY: f
f: format ## Shortcut for format

# Default target
.DEFAULT_GOAL := help
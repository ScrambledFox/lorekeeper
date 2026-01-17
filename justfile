# LoreKeeper Monorepo Justfile
# Run commands with: just <command>
# List all commands: just --list

set shell := ["bash", "-c"]
set dotenv-load := true

API_DIR := "lorekeeper-api"
VENV_DIR := ".venv"


list:
    @echo "Available commands:"
    @just --list


# ============================================================================
# Setup & Environment
# ============================================================================

# Initialize shared venv and install API dependencies
setup:
    @echo "🔧 Setting up LoreKeeper monorepo (shared venv)..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv sync
    @echo "✅ Shared venv ready at {{VENV_DIR}}"

# Update dependencies to latest versions
update:
    @echo "📦 Updating dependencies..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv sync --upgrade
    @echo "✅ Dependencies updated!"

# ============================================================================
# Development Server
# ============================================================================

# Run development API server with hot reload
dev:
    @echo "🚀 Starting API development server..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run API server in production mode
run:
    @echo "🚀 Starting API server..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run entire stack with Docker Compose
up:
    @echo "🐳 Starting Docker stack..."
    @cd {{API_DIR}} && docker-compose up --build

# Run Docker stack in background
up-d:
    @echo "🐳 Starting Docker stack in background..."
    @cd {{API_DIR}} && docker-compose up -d --build

# Stop Docker stack
down:
    @echo "🛑 Stopping Docker stack..."
    @cd {{API_DIR}} && docker-compose down

# View Docker logs
logs service="":
    @cd {{API_DIR}} && if [ -z "{{ service }}" ]; then \
        docker-compose logs -f; \
    else \
        docker-compose logs -f {{ service }}; \
    fi

# Restart Docker services
restart service="":
    @cd {{API_DIR}} && if [ -z "{{ service }}" ]; then \
        docker-compose restart; \
    else \
        docker-compose restart {{ service }}; \
    fi

# ============================================================================
# Database
# ============================================================================

# Start PostgreSQL in Docker
# Note: ensures API stack uses lorekeeper-api/docker-compose.yml
# even when run from repo root.
db-up:
    @echo "🗄️  Starting PostgreSQL..."
    @cd {{API_DIR}} && docker-compose up -d postgres

# Stop PostgreSQL
db-down:
    @echo "🛑 Stopping PostgreSQL..."
    @cd {{API_DIR}} && docker-compose down postgres

# Create a new database migration
db-migrate name:
    @echo "📝 Creating migration: {{ name }}"
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run alembic revision --autogenerate -m "{{ name }}"

# Run pending migrations
db-upgrade:
    @echo "⬆️  Running migrations..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run alembic upgrade head

# Rollback last migration
db-downgrade:
    @echo "⬇️  Rolling back migration..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run alembic downgrade -1

# View migration history
db-history:
    @echo "📜 Migration history:"
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run alembic history

# ============================================================================
# Testing
# ============================================================================

# Run all tests
test:
    @echo "🧪 Running tests..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run pytest

# Run tests with verbose output
test-v:
    @echo "🧪 Running tests (verbose)..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run pytest -v

# Run tests with coverage report
test-cov:
    @echo "🧪 Running tests with coverage..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run pytest --cov=lorekeeper --cov-report=html --cov-report=term
    @echo "📊 Coverage report generated in lorekeeper-api/htmlcov/index.html"

# Run specific test file
test-file file:
    @echo "🧪 Running tests in {{ file }}..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run pytest {{ file }} -v

# Run tests matching pattern
test-k pattern:
    @echo "🧪 Running tests matching '{{ pattern }}'..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run pytest -k "{{ pattern }}" -v

# ============================================================================
# Code Quality
# ============================================================================

# Format code with Black
fmt:
    @echo "🎨 Formatting code..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run black lorekeeper
    @echo "✅ Code formatted!"

# Check code with Ruff
lint:
    @echo "🔍 Linting code..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run ruff check lorekeeper

# Fix linting issues with Ruff
lint-fix:
    @echo "🔧 Fixing linting issues..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run ruff check --fix lorekeeper

# Type check with pyright
type-check:
    @echo "🔎 Type checking..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv run pyright lorekeeper

# Run all quality checks
check: fmt lint type-check
    @echo "✅ All checks passed!"

# ============================================================================
# Dependencies
# ============================================================================

# Add a new production dependency
add package:
    @echo "📦 Adding dependency: {{ package }}"
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv pip install {{ package }}
    @echo "✅ Dependency added!"

# Add a new dev dependency
add-dev package:
    @echo "📦 Adding dev dependency: {{ package }}"
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv pip install --dev {{ package }}
    @echo "✅ Dev dependency added!"

# Show outdated dependencies
outdated:
    @echo "🔍 Checking for outdated dependencies..."
    @cd {{API_DIR}} && UV_PROJECT_ENVIRONMENT=../{{VENV_DIR}} uv pip list --outdated

# ============================================================================
# API Documentation
# ============================================================================

# Open API docs (requires server running)
docs:
    @echo "📖 Opening API documentation..."
    @cd {{API_DIR}} && (open http://localhost:8000/docs || xdg-open http://localhost:8000/docs)

# Open ReDoc documentation (requires server running)
redoc:
    @echo "📖 Opening ReDoc documentation..."
    @cd {{API_DIR}} && (open http://localhost:8000/redoc || xdg-open http://localhost:8000/redoc)

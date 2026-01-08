# Development Guide for LoreKeeper

This project uses [UV](https://astral.sh/blog/uv) for fast Python package and environment management and [Just](https://just.systems/) for convenient command shortcuts.

## Prerequisites

- Python 3.11 or higher
- UV (install via `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Just (install via `brew install just` on macOS or see https://just.systems/)
- Docker & Docker Compose (for running Postgres)

## Quick Start

### Option 1: Local Development (Fastest)

```bash
just setup        # Install dependencies
just db-up        # Start PostgreSQL
just dev          # Start development server with hot-reload
```

API will be available at `http://localhost:8000/docs`

### Option 2: Docker Stack (Complete Setup)

```bash
just dev-full     # Start Postgres + API with Docker
```

API will be available at `http://localhost:8000/docs`

## Just Commands Reference

### Setup & Environment

```bash
just setup        # Initialize project and install dependencies
just update       # Update all dependencies to latest versions
just help         # Show this help message
just info         # Show environment info
```

### Development Server

```bash
just dev          # Start development server with hot-reload (local)
just run          # Start API server in production mode
just dev-full     # Start entire Docker stack (Postgres + API)
just up           # Start Docker stack with hot-reload
just up-d         # Start Docker stack in background
just down         # Stop Docker stack
just restart api  # Restart API container
just logs         # View Docker logs for all services
just logs api     # View only API logs
just logs postgres # View only PostgreSQL logs
```

### Testing

```bash
just test         # Run all tests
just test-v       # Run tests with verbose output
just test-cov     # Run tests with coverage report
just test-file path/to/test.py    # Run specific test file
just test-k pattern               # Run tests matching pattern
```

### Code Quality

```bash
just fmt          # Format code with Black
just lint         # Check code with Ruff
just lint-fix     # Auto-fix linting issues
just type-check   # Type checking with mypy
just check        # Run all checks (fmt + lint + type-check)
just verify       # Run tests + all checks (recommended pre-commit)
```

### Database Management

```bash
just db-up        # Start PostgreSQL container
just db-down      # Stop PostgreSQL container
just db-migrate "Migration name"  # Create new migration
just db-upgrade   # Run pending migrations
just db-downgrade # Rollback last migration
just db-history   # View migration history
```

### Dependencies

```bash
just add package-name      # Add production dependency
just add-dev package-name  # Add development dependency
just update               # Update all dependencies
just outdated             # Show outdated packages
```

### Utilities

```bash
just clean        # Remove cache and build files
just clean-all    # Remove cache + Docker volumes + containers
just docs         # Open API documentation (requires server running)
just redoc        # Open ReDoc documentation (requires server running)
```

### Workflow Commands

```bash
just start        # Full setup: dependencies + database + dev server
just verify       # Test + quality check (recommended before commit)
just build        # Full build workflow (clean + setup + test + check)
```

## Detailed Setup Instructions

### 1. Install UV

If you don't have UV installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or via pip:

```bash
pip install uv
```

### 2. Install Just

```bash
# macOS
brew install just

# Linux (Ubuntu/Debian)
sudo apt-get install just

# Other systems
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin
```

### 3. Install Dependencies

```bash
just setup
```

This will:
- Create a Python virtual environment at `.venv/`
- Install all dependencies from `pyproject.toml`
- Install dev dependencies (pytest, black, ruff, mypy)

### 4. Run PostgreSQL

```bash
just db-up
```

Or use Docker Compose directly:

```bash
docker-compose up -d postgres
```

### 5. Start Development Server

Choose one:

**Local (recommended for fast iteration):**
```bash
just dev
```

**Docker (full containerized stack):**
```bash
just dev-full
```

The API will be available at `http://localhost:8000`.

## Project Structure

```
lorekeeper/
├── api/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Settings with type hints
│   └── utils.py          # Generic utilities (ApiResponse, etc.)
├── db/
│   ├── __init__.py
│   ├── database.py       # SQLAlchemy session management
│   ├── models.py         # ORM models (World, Entity, Document, etc.)
│   └── init.sql          # Database initialization
├── indexer/
│   ├── __init__.py
│   └── chunker.py        # Document chunking with type hints
└── tests/
    ├── __init__.py
    └── test_typing.py    # Type hint verification tests
```

## Type Hints

This project uses comprehensive type hints throughout:

- **Function signatures**: All functions have parameter and return type annotations
- **SQLAlchemy models**: Using modern `Mapped[Type]` syntax
- **Generic types**: `ApiResponse[T]`, custom generics for flexibility
- **Async support**: Proper `AsyncGenerator` and async context types
- **UUID support**: PostgreSQL-native UUID types

Type checking is performed with **MyPy**:

```bash
just type-check   # Run mypy to verify all types
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://lorekeeper:lorekeeper_dev_password@localhost:5432/lorekeeper
ENVIRONMENT=development
```

### Settings

See `lorekeeper/api/config.py` for all configuration options:
- Database pool settings
- CORS configuration
- Pagination defaults
- API metadata

## Typical Development Workflow

### Starting Development

```bash
# First time setup
just setup

# Start database
just db-up

# Start development server
just dev

# In another terminal, run tests
just test-v
```

### Making Changes

```bash
# Make your code changes
# Editor will automatically reload server (hot-reload)

# Run tests to verify
just test

# Format and lint before committing
just verify
```

### Pre-Commit Checklist

```bash
# Run all verifications (tests + formatting + linting + types)
just verify

# If any issues, auto-fix them
just lint-fix
just fmt

# Then verify again
just verify

# Commit when all green!
```

## Docker Compose Details

The `docker-compose.yml` file defines two services:

### PostgreSQL (postgres:16-alpine)

- Port: `5432`
- Database: `lorekeeper`
- User: `lorekeeper`
- Password: `lorekeeper_dev_password` (dev only!)
- Extensions: `uuid-ossp`
- Health check: Automatic

### FastAPI API (Python 3.11)

- Port: `8000`
- Framework: FastAPI with Uvicorn
- Mode: Development with auto-reload
- Volume mounts: Live code editing

## Accessing the API

### Interactive Documentation

```bash
# Swagger UI
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc

# OpenAPI JSON
http://localhost:8000/openapi.json
```

### Health Check

```bash
curl http://localhost:8000/health
# {"status": "healthy"}

curl http://localhost:8000/
# {"status": "ok", "service": "LoreKeeper", "version": "0.1.0"}
```

## IDE Setup

### VS Code

Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- Ruff (charliermarsh.ruff)
- Thunder Client or REST Client (for API testing)

### PyCharm

1. Open project settings
2. Go to Project > Python Interpreter
3. Add new interpreter > Add Local Interpreter
4. Select the `.venv` directory in the project root
5. Configure code style to match Black (line length: 100)

## Troubleshooting

### Virtual Environment Issues

If `source .venv/bin/activate` doesn't work on Windows:

```bash
.venv\Scripts\activate
```

For PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

### PostgreSQL Connection Issues

Check if Docker is running and containers are healthy:

```bash
docker-compose ps
docker-compose logs postgres
```

Restart services:

```bash
just down
just db-up
```

### Port Already in Use

If ports 5432 (Postgres) or 8000 (API) are already in use:

```bash
# Kill existing containers
docker-compose down -v

# Start fresh
just dev-full
```

### UV or Just Commands Not Found

Ensure tools are in your PATH:

```bash
which uv
which just

# If not found, reinstall as shown in prerequisites section
```

### Dependencies Not Installing

Clear UV cache and reinstall:

```bash
rm -rf .venv
just setup
```

### Type Checking Failures

Run mypy with verbose output:

```bash
uv run mypy lorekeeper --show-error-codes
```

## Testing

### Running Tests

```bash
# All tests
just test

# Verbose output
just test-v

# Specific file
just test-file lorekeeper/tests/test_typing.py

# Matching pattern
just test-k "chunker"

# With coverage
just test-cov
```

### Writing Tests

Tests should be placed in `lorekeeper/tests/` with `test_` prefix:

```python
from typing import Any

def test_my_function() -> None:
    """Test description."""
    result: Any = my_function()
    assert result is not None
```

All tests must have type hints on function signatures.

## Code Style Guide

- **Line length**: 100 characters
- **Formatter**: Black
- **Linter**: Ruff
- **Type checker**: MyPy
- **Python version**: 3.11+

```bash
# Ensure code matches style before committing
just check
```

## Version Control

Before committing:

```bash
# Run full verification
just verify

# If there are any failures, fix and try again
just verify
```

## Next Steps

- See [README.md](README.md) for Phase 1 implementation plan
- See [JUSTFILE.md](JUSTFILE.md) for detailed Just command reference
- Check Milestone B for database migrations and CRUD endpoints


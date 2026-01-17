# LoreKeeper Monorepo Development Guide

This monorepo uses [UV](https://astral.sh/blog/uv) for Python package and environment management and [Just](https://just.systems/) for command shortcuts. The shared Python virtual environment lives at the repo root: `.venv/`.

## Prerequisites

- Python 3.11 or higher
- UV (install via `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Just (install via `brew install just` on macOS or see https://just.systems/)
- Docker & Docker Compose (for running Postgres)

## Quick Start

```bash
just setup        # Install dependencies into the shared venv
just db-up        # Start PostgreSQL
just dev          # Start API dev server with hot-reload
```

API docs: http://localhost:8000/docs

## Shared venv behavior

All root-level `just` commands run the API commands from `lorekeeper-api` but direct UV to use the shared `.venv/` at the monorepo root.

If you prefer project-local environments instead, run the `just` commands inside `lorekeeper-api/` directly.

## Common Commands (Root)

```bash
just setup        # Initialize shared venv + install API dependencies
just update       # Update dependencies to latest versions
just dev          # Start API dev server
just run          # Start API server (prod)
just db-up        # Start PostgreSQL container
just db-down      # Stop PostgreSQL container
just test         # Run tests
just fmt          # Format code with Black
just lint         # Lint with Ruff
just type-check   # Type check with pyright
just docs         # Open Swagger UI
just redoc        # Open ReDoc
```

## Service-Specific Docs

- API development details and deeper context live in [lorekeeper-api/DEVELOPMENT.md](lorekeeper-api/DEVELOPMENT.md)
- API commands reference is in [JUSTFILE.md](JUSTFILE.md)

## Monorepo Structure

```
/ (repo root)
├── lorekeeper-api/       # FastAPI + Postgres + RAG retrieval
├── lorekeeper-frontend/  # React UI
├── lorekeeper-bookgen/   # Book generation service
├── lorekeeper-loregen/   # Lore generation service
├── .venv/                # Shared Python virtual environment
├── justfile              # Root command entrypoint
└── DEVELOPMENT.md        # This guide
```

# Justfile Quick Reference

This project uses [Just](https://just.systems/) for easy command execution.

## Installation

If you don't have `just` installed:

```bash
# macOS
brew install just

# Linux (Ubuntu/Debian)
sudo apt-get install just

# Other systems
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/bin
```

## Quick Start Commands

### Get Started Immediately
```bash
just setup        # Install dependencies
just dev          # Start development server (http://localhost:8000)
just db-up        # Start PostgreSQL
```

### One-Command Setups
```bash
just start        # Full setup: dependencies + database + dev server
just dev-full     # Start entire Docker stack (Postgres + API)
```

## Common Commands

### Development Server
```bash
just dev          # Hot-reload development server
just run          # Production server
just logs         # View Docker logs
```

### Testing
```bash
just test         # Run all tests
just test-v       # Run with verbose output
just test-cov     # Run with coverage report
just test-k pattern  # Run tests matching pattern
just test-file path  # Run specific test file
```

### Code Quality
```bash
just fmt          # Format code with Black
just lint         # Check code with Ruff
just lint-fix     # Auto-fix linting issues
just type-check   # Type checking with mypy
just check        # Run all checks (fmt + lint + type-check)
just verify       # Test + check workflow
```

### Database
```bash
just db-up        # Start PostgreSQL container
just db-down      # Stop PostgreSQL container
just db-migrate "Add users table"  # Create migration
just db-upgrade   # Run migrations
just db-downgrade # Rollback last migration
just db-history   # View migration history
```

### Docker
```bash
just up           # Start entire stack with hot-reload
just up-d         # Start stack in background
just down         # Stop stack
just restart api  # Restart API service
just logs         # View all logs
just logs postgres # View postgres logs only
```

### Dependencies
```bash
just add package-name      # Add production dependency
just add-dev package-name  # Add dev dependency
just update               # Update all dependencies
just outdated             # Show outdated packages
```

### Utilities
```bash
just clean        # Remove cache/build files
just clean-all    # Remove cache + Docker volumes
just info         # Show environment info
just docs         # Open API docs (http://localhost:8000/docs)
just redoc        # Open ReDoc docs (http://localhost:8000/redoc)
```

## Workflow Examples

### Start Fresh Development Session
```bash
just clean
just setup
just db-up
just dev
```

### Run Tests Before Commit
```bash
just verify
```

### Deploy/Build Locally
```bash
just build
```

### Full Docker Stack
```bash
just dev-full
# Now access at http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Tips

- Run `just` or `just help` to see all available commands
- Commands with parameters use syntax like `just db-migrate "My migration name"`
- Run `just info` to verify your environment setup
- Use `just logs service-name` to follow logs from specific containers
- The `--list` flag shows descriptions: `just --list`

## Behind the Scenes

The justfile automates common development tasks by wrapping:
- **uv**: Python package management
- **pytest**: Testing framework
- **black**: Code formatting
- **ruff**: Linting
- **mypy**: Type checking
- **alembic**: Database migrations
- **docker-compose**: Container orchestration

# UV Setup Guide

This project uses [uv](https://github.com/astral-sh/uv) for fast Python dependency management.

## Setup (First Time)

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create virtual environment
uv venv

# 3. Activate it
source .venv/bin/activate

# 4. Install dependencies (includes dev tools: ruff, pytest, mypy)
uv pip install -e ".[dev]"

# 5. Run the app
./start.sh
```

## Daily Usage

```bash
# Activate virtual environment
source .venv/bin/activate

# Format code before committing
ruff format .

# Check code quality
ruff check .

# Auto-fix issues
ruff check --fix .

# Run the app
./start.sh
```

## Adding Dependencies

Edit `pyproject.toml`:
- Production deps: `[project.dependencies]`
- Dev deps: `[dependency-groups]` dev section

Then reinstall:
```bash
uv pip install -e ".[dev]"
```

## Why uv?

**10-100x faster** than pip with better dependency resolution.


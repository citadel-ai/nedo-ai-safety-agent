# Quick Start

## Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup project
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Setup frontend
cd frontend && npm install && cd ..

# Configure environment
cp env_template.txt .env
# Edit .env with your Google Cloud credentials

# Run
./start.sh
```

## Daily Commands

```bash
# Activate environment
source .venv/bin/activate

# Format code
ruff format .

# Check code
ruff check .

# Run app
./start.sh
```

## Adding Dependencies

Edit `pyproject.toml`:
- Production: `[project.dependencies]`
- Dev: `[dependency-groups]` dev section

Then run: `uv pip install -e ".[dev]"`

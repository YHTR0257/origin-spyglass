#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "Using uv: $(command -v uv)"
uv --version

# Create venv + install runtime/dev dependencies from pyproject.toml.
uv sync --all-groups

echo "Setup complete."
echo "Run checks with: uv run ruff check . && uv run mypy src tests"

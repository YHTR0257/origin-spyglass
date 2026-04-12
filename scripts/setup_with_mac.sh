#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ──────────────────────────────────────────────
# 1. prek (pre-commit runner)
# ──────────────────────────────────────────────
if ! command -v prek >/dev/null 2>&1; then
  echo "[prek] Installing..."
  pip install prek --quiet
fi
echo "[prek] $(prek --version 2>/dev/null || echo 'installed')"

# ──────────────────────────────────────────────
# 2. uv (Python package manager)
# ──────────────────────────────────────────────
if ! command -v uv >/dev/null 2>&1; then
  echo "[uv] Installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "[uv] $(uv --version)"

# Install backend Python dependencies
echo "[uv] Installing backend dependencies..."
cd "$REPO_ROOT/backend"
uv sync --all-groups
cd "$REPO_ROOT"

# ──────────────────────────────────────────────
# 3. pnpm (Node.js package manager)
# ──────────────────────────────────────────────
if ! command -v pnpm >/dev/null 2>&1; then
  echo "[pnpm] Installing..."
  curl -fsSL https://get.pnpm.io/install.sh | sh -
  export PATH="$HOME/.local/share/pnpm:$PATH"
fi
echo "[pnpm] $(pnpm --version)"

# Install frontend dependencies (if package.json exists)
if [ -f "$REPO_ROOT/frontend/package.json" ]; then
  echo "[pnpm] Installing frontend dependencies..."
  pnpm --dir "$REPO_ROOT/frontend" install
fi

# ──────────────────────────────────────────────
# 4. typos (spell checker)
# ──────────────────────────────────────────────
if ! command -v typos >/dev/null 2>&1; then
  echo "[typos] Installing..."
  if command -v cargo >/dev/null 2>&1; then
    cargo install typos-cli --quiet
  elif command -v brew >/dev/null 2>&1; then
    brew install typos-cli
  else
    echo "[typos] WARNING: cargo and brew not found. Install manually: https://github.com/crate-ci/typos"
  fi
fi
command -v typos >/dev/null 2>&1 && echo "[typos] $(typos --version)"

# ──────────────────────────────────────────────
# 5. gitleaks (secret scanner)
# ──────────────────────────────────────────────
if ! command -v gitleaks >/dev/null 2>&1; then
  echo "[gitleaks] Installing..."
  if command -v brew >/dev/null 2>&1; then
    brew install gitleaks
  else
    echo "[gitleaks] WARNING: brew not found. Install manually: https://github.com/gitleaks/gitleaks"
  fi
fi
command -v gitleaks >/dev/null 2>&1 && echo "[gitleaks] $(gitleaks version)"

# ──────────────────────────────────────────────
# 6. pre-commit hooks 登録 (prek)
# ──────────────────────────────────────────────
echo "[prek] Installing git hooks..."
prek install

echo ""
echo "Setup complete!"
echo "  Backend:  cd backend && uv run uvicorn src.app.main:app --reload"
echo "  Frontend: cd frontend && pnpm dev"

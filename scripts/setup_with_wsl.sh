#!/usr/bin/env bash
# WSL (Debian) セットアップスクリプト
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ──────────────────────────────────────────────
# ヘルパー
# ──────────────────────────────────────────────
latest_gh_release() {
  # $1: owner/repo  → 最新タグ名を返す
  curl -fsSL "https://api.github.com/repos/$1/releases/latest" \
    | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"\(.*\)".*/\1/'
}

# ──────────────────────────────────────────────
# 0. 基本パッケージ
# ──────────────────────────────────────────────
echo "[apt] Updating package list..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  curl ca-certificates git python3 python3-pip unzip

# ──────────────────────────────────────────────
# 1. prek (pre-commit runner)
# ──────────────────────────────────────────────
if ! command -v prek >/dev/null 2>&1; then
  echo "[prek] Installing..."
  pip3 install prek --quiet --break-system-packages
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
# 3. Node.js + pnpm
# ──────────────────────────────────────────────
if ! command -v node >/dev/null 2>&1; then
  echo "[node] Installing via NodeSource (LTS)..."
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo bash -
  sudo apt-get install -y nodejs
fi
echo "[node] $(node --version)"

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
# 4. typos (spell checker) — GitHub Releases からバイナリ取得
# ──────────────────────────────────────────────
if ! command -v typos >/dev/null 2>&1; then
  echo "[typos] Installing..."
  TYPOS_TAG="$(latest_gh_release 'crate-ci/typos')"
  TYPOS_URL="https://github.com/crate-ci/typos/releases/download/${TYPOS_TAG}/typos-${TYPOS_TAG}-x86_64-unknown-linux-musl.tar.gz"
  curl -fsSL "$TYPOS_URL" | tar -xz -C /tmp
  sudo install -m 755 /tmp/typos /usr/local/bin/typos
  rm -f /tmp/typos
fi
echo "[typos] $(typos --version)"

# ──────────────────────────────────────────────
# 5. gitleaks (secret scanner) — GitHub Releases からバイナリ取得
# ──────────────────────────────────────────────
if ! command -v gitleaks >/dev/null 2>&1; then
  echo "[gitleaks] Installing..."
  GITLEAKS_TAG="$(latest_gh_release 'gitleaks/gitleaks')"
  GITLEAKS_VER="${GITLEAKS_TAG#v}"
  GITLEAKS_URL="https://github.com/gitleaks/gitleaks/releases/download/${GITLEAKS_TAG}/gitleaks_${GITLEAKS_VER}_linux_x64.tar.gz"
  curl -fsSL "$GITLEAKS_URL" | tar -xz -C /tmp gitleaks
  sudo install -m 755 /tmp/gitleaks /usr/local/bin/gitleaks
  rm -f /tmp/gitleaks
fi
echo "[gitleaks] $(gitleaks version)"

# ──────────────────────────────────────────────
# 6. pre-commit hooks 登録 (prek)
# ──────────────────────────────────────────────
echo "[prek] Installing git hooks..."
prek install

echo ""
echo "Setup complete!"
echo "  Backend:  cd backend && uv run uvicorn src.app.main:app --reload"
echo "  Frontend: cd frontend && pnpm dev"

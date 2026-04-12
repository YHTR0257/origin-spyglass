# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

LLM agent development boilerplate with a FastAPI backend and a Next.js 15 frontend (frontend is a placeholder — no `src/` yet). Uses Docker Compose for running services, `uv` for Python dependency management, and `prek` (not `pre-commit`) for Git hooks.

<important>

## dev process

1. **design**: 欲しい機能や修正内容をユーザーが説明する
2. **explore**: コード探索スキルで関連ファイルと影響範囲を調査して報告する
3. **translate**: 変更内容をコード修正の指示に翻訳する
4. **implement**: コード修正スキルで実装する
5. **test**: backend の場合は pytest、frontend の場合は Next.js のテストランナーでテストを実行する
6. **review**: 変更内容を要約してユーザーに報告する

</important>

## Commands

### Docker (primary workflow)

```bash
cp .env.example .env   # first-time setup
make build             # docker compose build
make up                # docker compose up -d
make down              # docker compose down
make logs              # docker compose logs -f
```

### Backend (local, without Docker)

```bash
# from repo root
cd backend
uv sync --all-groups                                              # install deps
uv run uvicorn app.main:app --app-dir src --reload               # dev server

# tests
uv run pytest                                                    # all tests
uv run pytest tests/path/to/test_file.py::test_name             # single test

# lint / format
uv run ruff check --fix .
uv run ruff format .
uv run mypy src
```

### Frontend (placeholder — Next.js 15)

```bash
cd frontend
pnpm install
pnpm dev              # Next.js dev server
pnpm lint             # ESLint
pnpm lint:fix         # ESLint --fix
pnpm format           # Prettier --write
```

### Pre-commit hooks (prek)

```bash
# Install prek: https://prek.j178.dev/installation/
make uv-setup         # sets up uv and runs uv sync --all-groups
prek install          # install git hook
prek run              # run on staged files
prek run --all-files  # run on entire repo
```

## Architecture

```
llm-agent-boilerplate/
├── backend/                  # Python FastAPI service
│   ├── src/app/
│   │   ├── main.py           # app factory (create_app)
│   │   ├── api/              # routers (health.py)
│   │   ├── schemas/          # Pydantic response models
│   │   └── utils/            # settings (Pydantic Settings, .env)
│   ├── tests/
│   └── pyproject.toml        # uv/ruff/mypy/pytest config
├── frontend/                 # Next.js 15 app (stub — no src/ yet)
│   └── package.json
├── docker-compose.yml        # backend service only
├── prek.toml                 # pre-commit hook definitions
└── Makefile
```

### Backend internals

- `create_app()` in [backend/src/app/main.py](backend/src/app/main.py) builds the FastAPI instance and registers routers.
- Settings are loaded via `get_settings()` (Pydantic Settings + `.env`). The cached settings object reads `APP_NAME` and `ENVIRONMENT`.
- `BACKEND_PORT` in `.env` controls both Docker port mapping and the uvicorn bind port (default `8000`).

### Tooling

- **prek.toml** drives all pre-commit hooks: yaml/toml checks, ruff (backend only), typos, gitleaks, and ESLint (frontend only). Uses `prek`, not the `pre-commit` CLI.
- **ruff** is configured in `backend/pyproject.toml` with `line-length = 100`, rules `E F I UP B`, and `src = ["src", "tests"]`.
- **mypy** is strict (`disallow_untyped_defs`, `warn_return_any`).

# CLAUDE.md

This file provides guidance to coding agents when working in ORIGIN-SPYGLASS.

## Overview

ORIGIN-SPYGLASS is an agent system for research workflows. It orchestrates multi-node processing across collection, structuring, synthesis, critique, and persistence.

Current codebase status:

- FastAPI backend with minimal APIs (`/v1/health`, `/v1/models`, `/v1/chat/completions`)
- Frontend scaffold and Docker deployment
- Node-based architecture currently under phased implementation

<important>

## Dev process

1. **design**: ユーザーの要件を確認し、スコープを定義する
2. **explore**: 関連ファイル、依存関係、既存テストを調査する
3. **translate**: 変更を実装可能な技術課題に分解する
4. **implement**: 最小変更で実装し、既存スタイルを維持する
5. **test**: backend は pytest、frontend は lint/test を実行する
6. **review**: 変更内容、影響範囲、未対応事項を要約する

</important>

## Node model

The system is designed around 13 nodes:

- Gatherer: Local Doc Loader, Semantic Retriever, Relation Explorer, API Fetcher, Visual Evidence Extractor, Tool Scout
- Processor: Content Identifier, Context Integrator
- Synthesizer: Gap Navigator
- Critic: Spyglass Critic
- Persister: Document Archiver, Relation Archiver, Semantic Knowledge Persister

Implementation tickets for remaining nodes are tracked in issues #7 to #17.

## Commands

### Docker (primary workflow)

```bash
cp config/.env.example .env
make build
make up
make down
make logs
```

### Backend (local, without Docker)

```bash
cd backend
uv sync --all-groups
uv run uvicorn app.main:app --app-dir src --reload

# tests
uv run pytest
uv run pytest tests/path/to/test_file.py::test_name

# lint / format
uv run ruff check --fix .
uv run ruff format .
uv run mypy src
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
pnpm lint
pnpm lint:fix
pnpm format
```

### Pre-commit hooks (prek)

```bash
# Install prek: https://prek.j178.dev/installation/
make uv-setup
prek install
prek run
prek run --all-files
```

## Repository architecture

### Current

```text
origin-spyglass/
├── backend/src/app/
│   ├── api/v1/
│   ├── schemas/
│   ├── utils/
│   └── main.py
├── backend/tests/
├── frontend/
├── config/
└── docs/issues/
```

### Target

```text
origin-spyglass/
├── backend/src/app/
│   ├── api/v1/
│   ├── services/
│   │   ├── gatherer/
│   │   ├── processor/
│   │   ├── synthesizer/
│   │   ├── critic/
│   │   └── persister/
│   ├── pipelines/
│   │   └── langgraph_research_graph.py
│   ├── integrations/
│   ├── schemas/
│   └── utils/
├── backend/tests/
│   ├── services/
│   ├── pipelines/
│   └── api/
├── docs/
│   ├── issues/
│   ├── repository-design.md
│   └── rewrite-plan.md
└── frontend/
```

## Agent implementation rules

- Keep API routers thin and move logic into node/services layers.
- Add or update tests for every behavior change.
- Preserve backward-compatible API contracts unless explicitly changed.
- Fail safely: on external dependency failure, return actionable errors.
- Use typed schemas for node inputs/outputs.

## Tooling notes

- `prek.toml` is the single source of truth for hooks.
- `ruff` and `mypy` configs are in `backend/pyproject.toml`.
- Prefer `uv` for Python dependency and command execution.

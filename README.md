# llm-agent-boilerplate

LLMエージェント開発の土台となるテンプレートリポジトリです。

## セットアップ

### 環境変数

```bash
cp .env.example .env
```

`BACKEND_PORT` を変更すると公開ポートを制御できます（例: `BACKEND_PORT=18000`）。

### Python 開発環境

```bash
make uv-setup
```

`uv` が未導入なら `scripts/setup_uv.sh` がインストールし、`uv sync --all-groups` を実行します。

### Pre-commit フック

`prek` をインストールしてから有効化します。

```bash
# prek インストール: https://prek.j178.dev/installation/
prek install
```

## Docker 起動

```bash
make build
make up
```

health 確認:

```bash
curl http://localhost:${BACKEND_PORT:-8000}/health
```

ログ確認・停止:

```bash
make logs
make down
```

現時点の `docker-compose.yml` では backend のみ定義しています。

## ローカル起動（Docker を使わない場合）

### Backend

```bash
cd backend
uv run uvicorn app.main:app --app-dir src --reload
```

設定は Pydantic Settings で管理しています。`.env` に以下を置くと反映されます。

```dotenv
APP_NAME=llm-agent-boilerplate
ENVIRONMENT=local
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

## Pre-commit 運用（prek）

このリポジトリは `prek.toml` を唯一のフック設定として使用します。
`pre-commit` の YAML 設定は使わず、`prek` CLI を直接実行します。

```bash
prek run              # ステージされたファイルに対して実行
prek run --all-files  # リポジトリ全体に対して実行
prek validate         # 設定ファイルの妥当性確認
prek autoupdate       # フックの rev を更新
```

## 設定ファイル

| ファイル | 用途 |
| --- | --- |
| `.env.example` | 環境変数テンプレート |
| `prek.toml` | prek フック定義 |
| `backend/pyproject.toml` | Python プロジェクト定義・ruff/mypy/pytest 設定 |
| `backend/Dockerfile` | backend コンテナ定義 |
| `docker-compose.yml` | compose 定義（backend のみ） |
| `scripts/setup_uv.sh` | uv セットアップスクリプト |
| `Makefile` | uv / Docker 操作コマンド |

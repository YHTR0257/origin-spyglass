# ORIGIN-SPYGLASS

ORIGINシリーズのResearchを担当するエージェントシステムです。LLMを活用し、情報収集・統合・検証・保存までをノード連携で実行します。

## ノード定義

| Node 分類 | Node 名 | 責務と役割 | 主要ツール |
|:---|:---|:---|:---|
| **Gatherer (Local)** | **Local Doc Loader** | ローカルの PDF/MD/JSON/HTML をパースしテキスト化。形式別の前処理（OCR等）を行う。 | MarkItDown / PyMuPDF |
| **Gatherer (Vector)** | **Semantic Retriever** | Postgres(pgvector) からテーマに関連するセマンティックな断片を検索・取得する。 | LlamaIndex / PGVectorStore |
| **Gatherer (Graph)** | **Relation Explorer** | Neo4j から引用関係、共起概念、著者ネットワークを取得する。 | Cypher Query / Neo4j |
| **Gatherer (Online)** | **API Fetcher** | arXiv 等の外部 API から最新の論文メタデータやアブストラクトを収集する。 | arxiv-python / API |
| **Gatherer (Vision)** | **Visual Evidence Extractor** | 論文内の図表、グラフ、実験画像から情報を抽出。画像内のテキストや数値を構造化データに変換する。 | Vision LLM |
| **Gatherer (Tool)** | **Tool Scout** | 調査中に必要な新規ライブラリや API を探索し、サンドボックスで試用する。 | Web Search / Docker Sandbox |
| **Processor (ID)** | **Content Identifier** | 取得情報の種類（理論・手法・事実）を識別し、文脈に応じたタグ付けを行う。 | LLM によるタグ付け |
| **Processor (Merge)** | **Context Integrator** | ソース別の情報を単一の調査報告（統合 Markdown）として一貫性を持って再構成する。 | テンプレートエンジン / LLM |
| **Synthesizer** | **Gap Navigator** | 統合された知識を俯瞰し、未解決問題（ギャップ）を特定。解決の難易度と意義を評価する。 | Neo4j 探索 |
| **Critic** | **Spyglass Critic** | 調査の網羅性、エビデンス信頼性、ギャップ特定の妥当性を検証する。 | 信頼性評価プロンプト |
| **Persister (Doc)** | **Document Archiver** | 読み込まれた各文書を保存し、既存ナレッジネットワークとセマンティックに紐付ける。 | Postgres / Linker |
| **Persister (Rel)** | **Relation Archiver** | 文献調査で得た引用関係や概念関連をナレッジグラフ（Neo4j）へ記録する。 | Neo4j |
| **Persister (Res)** | **Semantic Knowledge Persister** | 調査報告とギャップを保存し、未解決問題の履歴を更新する。 | Postgres / Neo4j |

## 実装ステータス

- 現在の backend は FastAPI の最小実装（health/models/chat stub）です。
- ノード実装は段階的に移行します。
- Node 実装 issue:
	- #7 Semantic Retriever
	- #8 Relation Explorer
	- #9 API Fetcher
	- #10 Visual Evidence Extractor
	- #11 Tool Scout
	- #12 Content Identifier
	- #13 Context Integrator
	- #14 Gap Navigator
	- #15 Spyglass Critic
	- #16 Relation Archiver
	- #17 Semantic Knowledge Persister

## リポジトリ再設計（方針）

詳細は `docs/repository-design.md` を参照してください。

```text
origin-spyglass/
├── backend/
│   ├── src/app/
│   │   ├── api/v1/               # API Router（実行エントリ）
│   │   ├── services/             # 各 Service 実装（Node責務を分割）
│   │   │   ├── gatherer/
│   │   │   ├── processor/
│   │   │   ├── synthesizer/
│   │   │   ├── critic/
│   │   │   └── persister/
│   │   ├── pipelines/            # LangGraph定義と実行フロー
│   │   │   └── langgraph_research_graph.py
│   │   ├── integrations/         # pgvector, Neo4j, arXiv 等
│   │   ├── schemas/
│   │   └── utils/
│   └── tests/
│       ├── services/
│       ├── pipelines/
│       └── api/
├── docs/
│   ├── issues/
│   ├── repository-design.md
│   └── rewrite-plan.md
└── frontend/
```

## セットアップ

### 環境変数

```bash
cp config/.env.example .env
```

`BACKEND_PORT` と `FRONTEND_PORT` を変更すると公開ポートを制御できます。

### Python 開発環境

```bash
make uv-setup
```

`uv` が未導入なら `scripts/setup_uv.sh` がインストールし、`uv sync --all-groups` を実行します。

### Docker 起動

```bash
make build
make up
```

health 確認:

```bash
curl http://localhost:${BACKEND_PORT:-8000}/v1/health
```

ログ確認・停止:

```bash
make logs
make down
```

## ローカル起動（Docker を使わない場合）

### Backend

```bash
cd backend
uv sync --all-groups
uv run uvicorn app.main:app --app-dir src --reload
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

## テストと品質チェック

```bash
cd backend
uv run pytest
uv run ruff check --fix .
uv run ruff format .
uv run mypy src
```

```bash
prek run --all-files
```

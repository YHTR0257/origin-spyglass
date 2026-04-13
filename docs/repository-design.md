# ORIGIN-SPYGLASS Repository Design

## 目的

本ドキュメントは、ORIGIN-Spyglass の backend リポジトリ設計方針を定義する。
Node の定義と責務は [architecture.md](architecture.md) を、ユーザー視点の処理フローは [user-journey.md](user-journey.md) を参照。

## 設計原則

1. **tool ごとに責務とスキーマを閉じる** — 各 tool ディレクトリが入力/出力スキーマを持つ。複数 tool で共有が増えた段階で `schemas/` へ昇格させる
2. **tools はフラットに並べる** — サブカテゴリ（Gatherer / Processor 等）でディレクトリを切らない。カテゴリは命名規則とドキュメントで表現する
3. **API 層はオーケストレーションのみ** — ビジネスロジックを持たず、Spyglass グラフの呼び出しのみ行う
4. **外部依存は infra に閉じる** — Postgres / Neo4j / Vision LLM / arXiv クライアントは `infra/` のみが持つ
5. **spyglass_utils は origin_spyglass と同列** — ロギング・レートリミット・設定など横断的ユーティリティを分離して管理する

---

## ターゲット構成

```text
backend/src/
├── origin_spyglass/                        # メインパッケージ
│   ├── main.py                             # FastAPI アプリファクトリ
│   ├── security_headers.py
│   │
│   ├── api/                                # 入出力受付・例外変換のみ
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── chat.py
│   │       ├── health.py
│   │       └── models.py
│   │
│   ├── spyglass/                           # LangGraph オーケストレーション
│   │   ├── __init__.py
│   │   ├── graph.py                        # node / edge / state 定義
│   │   └── state.py                        # GraphState スキーマ
│   │
│   ├── tools/                              # ノード実装（フラット）
│   │   │
│   │   ├── local_doc_loader/               # Gatherer (Local)
│   │   │   ├── __init__.py
│   │   │   ├── converter.py
│   │   │   ├── cleaner.py
│   │   │   └── types.py                    # FrontmatterMeta 等 (local schema)
│   │   │
│   │   ├── semantic_retriever/             # Gatherer (Vector)
│   │   │   ├── __init__.py
│   │   │   └── types.py                    # 検索クエリ / 結果スキーマ
│   │   │
│   │   ├── relation_explorer/              # Gatherer (Graph)
│   │   │   ├── __init__.py
│   │   │   └── types.py                    # Cypher クエリ / グラフ結果スキーマ
│   │   │
│   │   ├── api_fetcher/                    # Gatherer (Online)
│   │   │   ├── __init__.py
│   │   │   └── types.py                    # arXiv レスポンス等スキーマ
│   │   │
│   │   ├── visual_evidence_extractor/      # Gatherer (Vision)
│   │   │   ├── __init__.py
│   │   │   └── types.py                    # 画像入力 / 構造化出力スキーマ
│   │   │
│   │   ├── content_identifier/             # Processor (ID)
│   │   │   ├── __init__.py
│   │   │   └── types.py                    # タグ付き断片スキーマ
│   │   │
│   │   ├── context_integrator/             # Processor (Merge)
│   │   │   ├── __init__.py
│   │   │   └── types.py                    # 統合 Markdown 出力スキーマ
│   │   │
│   │   ├── gap_navigator/                  # Synthesizer
│   │   │   ├── __init__.py
│   │   │   └── types.py                    # Gap スキーマ（難易度・意義・関連概念）
│   │   │
│   │   ├── spyglass_critic/                # Critic
│   │   │   ├── __init__.py
│   │   │   └── types.py                    # 検証結果・指摘スキーマ
│   │   │
│   │   ├── doc_relationship_persister/     # Persister (Doc)
│   │   │   ├── __init__.py
│   │   │   └── types.py                    # DocumentMetadata (doc_id 等)
│   │   │
│   │   ├── idea_relation_persister/        # Persister (Rel)
│   │   │   ├── __init__.py
│   │   │   ├── context_injector.py
│   │   │   ├── pipeline.py
│   │   │   ├── service.py
│   │   │   └── types.py
│   │   │
│   │   └── semantic_knowledge_persister/   # Persister (Res)
│   │       ├── __init__.py
│   │       └── types.py                    # ギャップ履歴・調査報告スキーマ
│   │
│   ├── schemas/                            # 複数 tool が共有するスキーマのみ
│   │   ├── __init__.py
│   │   ├── ask.py                          # AskRequest / AnswerResponse (API 境界)
│   │   ├── doc_relation.py                 # DocRelation / SourceType (共有済み)
│   │   ├── semantic_knowledge.py           # SemanticKnowledge (共有済み)
│   │   ├── health.py
│   │   └── openai.py
│   │
│   └── infra/                              # 外部サービスクライアント
│       ├── __init__.py
│       ├── graph_store.py                  # Neo4j クライアント
│       ├── vector_store.py                 # pgvector クライアント (未実装)
│       └── llm/
│           ├── __init__.py
│           ├── base.py
│           ├── clients.py
│           ├── openai_api.py
│           ├── utils.py
│           └── exceptions.py
│
└── spyglass_utils/                         # 横断ユーティリティ（origin_spyglass と同列）
    ├── __init__.py
    ├── settings.py                         # Pydantic Settings (.env 読み込み)
    ├── logging.py
    ├── output_filter.py
    └── rate_limiter.py
```

---

## スキーマ配置方針

| 状態 | 配置先 | 例 |
| :--- | :--- | :--- |
| tool 固有で他から参照なし | `tools/<tool>/types.py` | `FrontmatterMeta`、`Gap` |
| 複数 tool が参照する | `schemas/<name>.py` | `DocRelation`、`SemanticKnowledge` |
| API 境界（リクエスト/レスポンス） | `schemas/ask.py` 等 | `AskRequest`、`AnswerResponse` |

> 昇格タイミング: 2つ目の tool が `import` した時点で `schemas/` へ移動する。

---

## 既存ファイルの移行マッピング

| 現在のパス | 移行先 | 備考 |
| :--- | :--- | :--- |
| `local_doc_loader/` | `tools/local_doc_loader/` | ファイル構成はそのまま維持 |
| `relation_persister/` | `tools/idea_relation_persister/` | ディレクトリリネーム |
| `document_archiver/` | `tools/doc_relationship_persister/` | ディレクトリリネーム |
| `semantic_knowledge_archiver/` | `tools/semantic_knowledge_persister/` | ディレクトリリネーム |
| `schemas/` | `schemas/` | 共有スキーマはそのまま残留 |
| `infra/` | `infra/` | 変更なし |
| `spyglass_utils/` | `spyglass_utils/` | 変更なし（同列維持を明示） |

---

## 依存関係の境界

```
api/ ──────────────────▶ spyglass/graph.py
                              │
                              ▼
                         tools/<tool>/       ──▶ schemas/     (共有スキーマ参照)
                              │              ──▶ infra/        (外部サービスアクセス)
                              │              ──▶ spyglass_utils/ (ロギング・設定)
                              │
                         [tool → tool の直接 import は禁止。schemas/ 経由で接続する]
```

- `api/` → `spyglass/`・`schemas/` は許可
- `tools/` → `infra/`・`schemas/`・`spyglass_utils/` は許可
- `tools/` 間の直接 import は禁止（`schemas/` 経由で接続）
- `infra/` → `api/`・`tools/` への逆向き依存は禁止

---

## マイグレーション戦略

1. `tools/` ディレクトリを作成し、既存モジュールをリネームしながら移動する
2. `spyglass/` ディレクトリを作成し、LangGraph の graph / state を配置する
3. 各 tool の stub（`__init__.py` + `types.py`）を先に作り、スキーマ定義を確定させる
4. tool 実装を issue 単位で進め、段階的に `spyglass/graph.py` に接続する
5. Persister 群が揃った段階でデータ整合性テストを追加する（実行順序: Doc → Rel → Res）
6. Critic 導入後に品質ゲートを有効化する

---

## テスト戦略

| 種別 | 対象 | 配置 |
| :--- | :--- | :--- |
| Unit | 各 tool の正常系/異常系 | `tests/tools/<tool>/` |
| Integration | Postgres / Neo4j 接続 | `tests/infra/` |
| API | `/v1/chat/completions` E2E | `tests/api/v1/` |
| Regression | 同一入力での結果品質閾値 | `tests/regression/` |

---

## 完了条件

- 13 ノードの責務が `tools/` 以下にディレクトリ単位で分離されている
- 各 tool が `types.py`（ローカルスキーマ）を持つ
- 共有スキーマが `schemas/` に集約されている
- `spyglass/graph.py` が全 tool を接続している
- backend テストが主要経路をカバーしている
- このドキュメントと [architecture.md](architecture.md)・[user-journey.md](user-journey.md) の記述が実装状態と一致している

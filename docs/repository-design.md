# ORIGIN-SPYGLASS Repository Design

## 目的

本ドキュメントは、ORIGINシリーズのResearchエージェントを実装するためのリポジトリ設計方針を定義します。
主眼は以下です。

- ノード責務の分離
- 実装単位ごとのテスト容易性
- 外部依存（Postgres/pgvector、Neo4j、arXiv、Vision LLM）の差し替え容易性
- 段階移行中でも既存APIを維持する安全な変更

## 設計原則

1. ノードごとに入力/出力スキーマを定義する
2. API層はオーケストレーションのみ行い、ビジネスロジックを持たない
3. 外部サービスアクセスは integrations 層に閉じ込める
4. 失敗を前提に、リトライ・タイムアウト・フォールバックを標準化する
5. すべてのノードにユニットテストを用意する

## ターゲット構成

```text
backend/src/origin_spyglass/
├── api/
│   └── v1/
│       ├── chat.py
│       ├── health.py
│       └── models.py
├── services/
│   ├── gatherer/
│   │   ├── local_doc_loader.py
│   │   ├── semantic_retriever.py
│   │   ├── relation_explorer.py
│   │   ├── api_fetcher.py
│   │   ├── visual_evidence_extractor.py
│   │   └── tool_scout.py
│   ├── processor/
│   │   ├── content_identifier.py
│   │   └── context_integrator.py
│   ├── synthesizer/
│   │   └── gap_navigator.py
│   ├── critic/
│   │   └── spyglass_critic.py
│   └── persister/
│       ├── document_archiver.py
│       ├── relation_archiver.py
│       └── semantic_knowledge_persister.py
├── pipelines/
│   ├── research_pipeline.py
│   └── langgraph_research_graph.py
├── integrations/
│   ├── postgres/
│   ├── neo4j/
│   ├── arxiv/
│   └── vision/
├── schemas/
│   ├── node_io.py
│   ├── report.py
│   └── openai.py
└── utils/
    ├── settings.py
    ├── rate_limiter.py
    └── output_filter.py
```

## モジュール責務

- services: 各ノード責務を持つサービス実装
- pipelines: ノードを接続した実行シーケンス
- pipelines/langgraph_research_graph.py: LangGraph の node / edge / state 定義
- integrations: 外部サービスアクセスの実装
- schemas: API/Node共通スキーマ
- api: 入出力受付、認証、例外変換

## 既存ファイルの書き換え方針

以下を対象に段階的に書き換えます。

- `backend/src/app/main.py`: 依存注入とパイプライン登録の追加
- `backend/src/app/api/v1/chat.py`: stub応答からパイプライン呼び出しへ変更
- `backend/src/app/api/v1/models.py`: モデル列挙を設定駆動に拡張
- `backend/src/app/schemas/openai.py`: ノード追跡メタデータを追加
- `backend/src/app/utils/settings.py`: Postgres/Neo4j/arXiv/Vision設定を追加
- `backend/tests/api/v1/test_chat.py`: パイプライン連携前提で再構成

## マイグレーション戦略

1. ノード雛形とスキーマを先に導入する
2. chat API からパイプラインを呼ぶ経路を追加する
3. 各ノードを issue 単位で実装し、段階的に有効化する
4. Persister 群の導入後にデータ整合性テストを追加する
5. Critic 導入後に品質ゲートを有効化する

## テスト戦略

- Unit: 各ノード関数の正常系/異常系
- Integration: postgres/neo4j の接続テスト
- API: `/v1/chat/completions` のE2E相当
- Regression: 同一入力での結果品質の閾値検証

## 依存関係の境界

- services -> integrations は許可
- api -> services/pipelines は許可
- integrations -> api は禁止
- services 間の直接依存は最小化し、schemas 経由で接続

## 完了条件

- 13ノードの責務がコード上で分離されている
- 主要APIがノード実装を通じて動作する
- backendテストが主要経路をカバーしている
- README/CLAUDE/docs の記述が実装状態と一致している

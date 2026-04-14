name: translate
# translate
指示の翻訳スキル

ユーザーの指示を構造化し、コードに触る前に「何を・どこで・どう直すか」を明確にする。
翻訳結果をユーザーに提示し、確認を得てから次のステップに進む。

## 実行手順

### Step 0: 論点の抽出

ユーザーの発言からすべての指示を漏れなく列挙する。

**ルール**:
- 省略・統合・要約はしない。ユーザーが3つ言ったら3つ出す
- 「ついでに」「あと」「それと」の後に続く指示も独立した論点として扱う
- 感情表現（怒り、皮肉、強調）は論点の優先度と重大度の手がかりとして扱う。無視するな

### Step 1: 構造化された問題文への変換

各論点について、以下の項目を埋める:

| 項目 | 内容 |
|------|------|
| **対象層** | API / Orchestration / Node / Tool-Integration / Infra / Cross-Cutting / Frontend / 不明 |
| **スコープ** | 単一ファイル / 複数ファイル（同一モジュール内） / モジュール横断 |
| **問題の種類** | エラーが出る / 期待と異なる動作 / 未実装 / リファクタリング / 調査 |
| **エラー情報** | エラーメッセージがあれば記載。なければ「なし」 |
| **技術的な問題文** | ユーザーの指示をエンジニアリングの問題として再記述 |

「不明」が残る場合は、ユーザーに確認する。推測で埋めない。

### Step 2: リポジトリの具体箇所への紐付け

各論点を、spyglass リポジトリの具体的なファイル・モジュールに紐付ける。

**spyglass のモジュール対応表**:

| 層 | モジュール | 主な責務 |
|----|-----------|---------|
| Orchestration | `backend/src/origin_spyglass/pipelines/` | Spyglass (LangGraph) の実行、グラフ制御 |
| Node (Gatherer) | `backend/src/origin_spyglass/local_doc_loader/` | ローカル文書のパース、テキスト化、前処理 |
| Node (Persister - Doc) | `backend/src/origin_spyglass/doc_relationship_persister/` | 文書エンティティ・メタデータの保存 (Postgres/pgvector) |
| Node (Persister - Rel) | `backend/src/origin_spyglass/idea_relation_persister/` | 概念・引用関係のグラフ保存 (Neo4j) |
| Node (Persister - Res) | `backend/src/origin_spyglass/semantic_knowledge_archiver/` | 調査報告とギャップ履歴の保存 |
| API | `backend/src/origin_spyglass/api/` | FastAPI エンドポイント、リクエスト受付 |
| Tool / Infra | `backend/src/origin_spyglass/infra/` | LLM, Neo4j, VectorStore への具体的接続・操作 |
| Models | `backend/src/origin_spyglass/schemas/` | Pydantic スキーマ定義 |
| Cross-Cutting | `backend/src/spyglass_utils/` | ロギング、セキュリティ、フィルタ、レート制限 |
| Frontend | `frontend/` | UI |
| Tests | `backend/tests/` | ユニットテスト、統合テスト |

**出力フォーマット**:

```
## 翻訳結果

### 論点1: [ユーザーの原文から抜粋]
- 対象層: Node (Persister - Rel)
- スコープ: 単一ファイル
- 問題の種類: 期待と異なる動作
- エラー情報: なし
- 技術的な問題文: extractor.py で特定の引用フォーマットからエッジを抽出できていない
- 対象ファイル: `backend/src/origin_spyglass/idea_relation_persister/extractor.py`

### 論点2: ...
```

## 翻訳完了後

翻訳結果を提示し、ユーザーに確認を求める。

- 「この理解で合っていますか？」と必ず聞く
- ユーザーが修正した場合は翻訳結果を更新する
- ユーザーが承認したら `/explore` に進む

## 禁止事項

- 翻訳完了前にコードの修正に着手しない
- 「不明」を推測で埋めない。ユーザーに聞く
- 論点を統合・省略しない

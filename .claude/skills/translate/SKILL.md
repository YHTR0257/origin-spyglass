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
| **対象層** | API / Service / LLM / DB / Frontend / 不明 |
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
| API | `backend/src/origin_spyglass/api/` | FastAPI エンドポイント、リクエスト受付 |
| Service (ask) | `backend/src/origin_spyglass/services/ask/` | 質問応答ロジック、PropertyGraphStore 検索 |
| Service (index) | `backend/src/origin_spyglass/services/index/` | インデキシング、Neo4j への保存 |
| Service (documents) | `backend/src/origin_spyglass/services/documents/` | ドキュメント変換 (PDF/Word → Markdown) |
| LLM | `backend/src/origin_spyglass/llm/` | LLMクライアント管理、プロバイダー接続 |
| DB | `backend/src/origin_spyglass/db/` | Neo4j 接続管理 |
| Models | `backend/src/origin_spyglass/models/` | Pydantic スキーマ |
| Frontend | `frontend/` | UI |
| Config | `envs/` | Docker、環境設定 |
| Tests | `backend/tests/`, `tests/` | ユニットテスト、統合テスト |

**出力フォーマット**:

```
## 翻訳結果

### 論点1: [ユーザーの原文から抜粋]
- 対象層: Service (ask)
- スコープ: 単一ファイル
- 問題の種類: 期待と異なる動作
- エラー情報: なし
- 技術的な問題文: retrieval.py の検索クエリ構築で、エンティティの部分一致検索ができていない
- 対象ファイル: `backend/src/origin_spyglass/services/ask/retrieval.py`

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
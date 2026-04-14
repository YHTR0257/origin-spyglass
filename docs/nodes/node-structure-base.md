# Overview

- それぞれのノードは独立したモジュールとして実装され、明確な入出力型を持つ
- 一つのノードは責任範囲が明確な単一の処理パイプラインを提供する
- ノード間のデータフローは、FastAPI のエンドポイントや内部サービスを通じてオーケストレーションされる
- 例外は型付きで定義され、API レイヤーで適切な HTTP ステータスコードにマッピングされる

# Node Structure
- ノードの構成は、`node1/__init__.py` で公開されるパイプラインクラスを中心に整理される

推奨されるモジュール構成
```
node_name/.      # 役割が明確なモジュール単位で命名もわかりやすく簡潔なものに
├── __init__.py   # 公開インターフェース（パイプラインクラスなど）
├── types.py      # 入出力型、例外型定義
├── validation.py  # 入力バリデーションロジック
├── pipeline.py    # ノードの主要処理をオーケストレーションするパイプラインクラス
├── step1.py       # STEP1 の実装（例: データ前処理）
├── step2.py       # STEP2 の実装（例: LLM 呼び出し）
├── step3.py       # STEP3 の実装（例: 結果後処理）
└── ...            # 必要に応じて追加
```

テストは、`tests/` ディレクトリ内で同様の構成を持ち、各モジュールのテストを対応させる。
```
tests/
├── node_name/     # 対応するノード名のディレクトリ
│   ├── __init__.py
│   ├── _helpers.py         # テストで共通のフィクスチャやモックを定義
│   ├── test_validation.py  # validation.py のテスト
│   ├── test_pipeline.py    # pipeline.py のテスト
│   ├── test_step1.py       # step1.py のテスト
│   ├── test_step2.py       # step2.py のテスト
│   └── test_step3.py       # step3.py のテスト
└── ...              # 他のノードのテストディレクトリ
```

## Separation of Concerns
すべてを単一のファイルに詰め込むのではなく、役割ごとにモジュールをパーツに分割することで、コードの可読性と保守性を向上させる。

- モジュールパーツの責務
    - **__init__.py**: ノードの主要なパイプラインクラスを公開し、外部からの呼び出しをシンプルに保つ
    - **validation.py**: 入力データの検証とエラー定義
    - **pipeline.py**: ノードの全体的な処理フローの管理
        - 各ステップの実装は stepX.py に分割する
    - **types.py**: 入出力のデータモデルと例外クラスを定義し、API レイヤーでのエラーハンドリングを容易にする

---

# Best Practices

## types.py

### エラー型の命名
エラークラスはノード名をプレフィックスに付け、`ValidationError` 等の汎用名との衝突を避ける。

```python
# NG: 他のモジュールと衝突しやすい
class ValidationError(ValueError): ...

# OK
class IdeaRelationValidationError(ValueError):
    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"[validation] field={field} reason={reason}")
```

### バリデーション済み入力の型エイリアス
STEP1 通過後の型はエイリアスで表現する。再構築コストなしに「検証済み」の意図を型で示せる。

```python
ValidatedInput = NodeInput  # 型エイリアス（再構築なし）
```

---

## validation.py

### Fail-fast バリデーション
最初の違反で即座に raise する。詳細なエラーは `field` 属性で伝える。

```python
def validate(input: NodeInput) -> ValidatedInput:
    if not input.doc_id.strip():
        raise NodeValidationError("doc_id", "must not be empty")
    if not input.body_text.strip():
        raise NodeValidationError("body_text", "must not be empty")
    # クロスフィールド制約は Pydantic Field では表現できないため手動チェック
    if input.chunk_overlap >= input.chunk_size:
        raise NodeValidationError("chunk_overlap", f"must be < chunk_size ({input.chunk_size})")
    return input
```

---

## pipeline.py

### 依存をコンストラクタ注入する
外部依存（DB 接続、LLM クライアント等）はコンストラクタで受け取ることで、
テスト時に `MagicMock` を差し込める。モジュールグローバルへの依存は避ける。

```python
class NodePipeline:
    def __init__(self, store_manager: Neo4jGraphStoreManager, llm: LLM) -> None:
        self._store_manager = store_manager
        self._llm = llm

    def run(self, input: NodeInput) -> NodeOutput:
        ...
```

### run() は同期メソッド
llama-index の `PropertyGraphIndex.from_documents()` など、外部ライブラリが同期 I/O を持つ場合は
`run()` を同期にし、FastAPI ルーターで `asyncio.to_thread()` 経由で呼ぶ。

```python
# router
return await asyncio.to_thread(pipeline.run, body)
```

### Best-effort な処理は例外を握り潰して warnings に記録する
集計・計測など、失敗しても主要結果に影響しない処理は `try/except` でラップし、
`warnings` リストに記録して伝播させる。

```python
try:
    node_count = len(index.property_graph_store.get_triplets())
except Exception as exc:
    logger.warning("count unavailable: %s", exc)
    warnings.append("node/edge count unavailable")
```

---

## ルーター（`api/v1/<node>.py`）

### 薄いルーター + `_get_pipeline()` ファクトリ
ビジネスロジックはパイプラインに委譲し、ルーターは HTTP エラーマッピングのみを担う。
`_get_pipeline()` を独立した関数にすることで、テスト時に `monkeypatch` で差し替えられる。

```python
_graph_manager = Neo4jGraphStoreManager()   # モジュールレベルシングルトン
_llm_manager = LlmClientManager()

def _get_pipeline() -> NodePipeline:
    return NodePipeline(store_manager=_graph_manager, llm=_llm_manager.get_llm())

@router.post("/relations", status_code=201)
async def persist(body: NodeInput) -> NodeOutput:
    pipeline = _get_pipeline()
    try:
        return await asyncio.to_thread(pipeline.run, body)
    except NodeValidationError as e:
        raise HTTPException(422, detail=str(e)) from e
    except GraphStoreUnavailable as e:
        raise HTTPException(503, detail=str(e)) from e
    except ExtractionFailed as e:
        raise HTTPException(502, detail=str(e)) from e
    except PersistFailed as e:
        raise HTTPException(500, detail=str(e)) from e
```

---

## テスト

### `_helpers.py` にファクトリ関数をまとめる
各テストファイルで重複する入力生成ロジックは `_helpers.py` に切り出す。
`**overrides` パターンで個別フィールドの差し替えを可能にする。

```python
# tests/node_name/_helpers.py
def make_valid_input(**overrides: object) -> NodeInput:
    defaults = {"doc_id": "doc-001", "body_text": "...", ...}
    defaults.update(overrides)
    return NodeInput(**defaults)
```

### ルーターテストは `_get_pipeline` を monkeypatch する
`autouse=True` フィクスチャで正常系のデフォルトモックを設定し、
異常系テストは `side_effect` を個別に上書きする。

```python
@pytest.fixture(autouse=True)
def _patch_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    from origin_spyglass.api.v1 import node as node_module
    mock = MagicMock()
    mock.run.return_value = _SAMPLE_OUTPUT
    monkeypatch.setattr(node_module, "_get_pipeline", lambda: mock)
```

### 外部ライブラリの untyped import
`llama-index` など型スタブのないライブラリは各 import に `# type: ignore[import-untyped]` を付ける。
mypy の `[[tool.mypy.overrides]] ignore_missing_imports = true` は import エラーのみを抑制するため、
属性アクセスエラー（`[attr-defined]`）には個別に `# type: ignore[attr-defined]` が必要になる場合がある。

```python
from llama_index.core import PropertyGraphIndex  # type: ignore[import-untyped]
from llama_index.core.schema import TextNode     # type: ignore[import-untyped]

# 実行時には存在するが型スタブ上は未定義の属性
node_name: str = getattr(entity_node, "name", "")  # type: ignore[union-attr]
```

"""POST /v1/ideas/relations および POST /v1/ideas/relations/retrieval のエンドポイントテスト

パイプラインは _get_pipeline() / _get_retriever_pipeline() を monkeypatch で差し替えてテストする。
各 autouse フィクスチャで正常系のデフォルトモックを設定し、
各異常系テストは必要に応じて個別に side_effect を上書きする。

run() は同期メソッドだが asyncio.to_thread() 経由で呼ばれるため、
TestClient（anyio ベース）で問題なく動作する。
"""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from origin_spyglass.idea_relation_persister.types import (
    ExtractionFailed,
    GraphStoreUnavailable,
    IdeaRelationPersisterOutput,
    IdeaRelationValidationError,
    PersistFailed,
)
from origin_spyglass.idea_relation_retriever.types import (
    IdeaRelationRetrieverOutput,
    RelatedIdea,
)
from origin_spyglass.main import app

client = TestClient(app)

# --- Persister fixtures ---

_SAMPLE_PERSISTER_OUTPUT = IdeaRelationPersisterOutput(
    doc_id="doc-001",
    persisted=True,
    node_count=5,
    edge_count=4,
    elapsed_ms=123,
    warnings=[],
)

_VALID_PERSIST_BODY: dict[str, Any] = {
    "doc_id": "doc-001",
    "frontmatter": {
        "domain": "tech",
        "tags": ["ai"],
        "title": "Test",
        "created_at": "2026-04-14T00:00:00",
        "source_file": "test.md",
        "source_type": "local_markdown",
        "confidence": 0.9,
        "date": "2026-04-01",
    },
    "body_text": "Alice knows Bob. Bob works at Acme.",
    "chunk_size": 256,
    "chunk_overlap": 32,
}

# --- Retriever fixtures ---

_SAMPLE_RETRIEVER_OUTPUT = IdeaRelationRetrieverOutput(
    question="量子コンピュータとは？",
    answer="量子コンピュータは量子力学の原理を利用した計算機です。",
    related_ideas=[
        RelatedIdea(
            node_id="node-001",
            title="量子コンピュータ",
            body_snippet="量子コンピュータは量子力学の原理を...",
            relevance_score=0.92,
        )
    ],
    elapsed_ms=120,
    warnings=[],
)

_VALID_SEARCH_BODY: dict[str, Any] = {
    "question": "量子コンピュータとは？",
    "max_results": 10,
}


@pytest.fixture(autouse=True)
def _patch_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """全テストで _get_pipeline() を差し替え、実 LLM / Neo4j 接続を回避する。

    正常系は _SAMPLE_PERSISTER_OUTPUT を返す。
    異常系テストは各自で monkeypatch.setattr を上書きして side_effect を設定する。
    """
    from origin_spyglass.api.v1 import ideas as ideas_module

    mock_pipeline = MagicMock()
    mock_pipeline.run.return_value = _SAMPLE_PERSISTER_OUTPUT
    monkeypatch.setattr(ideas_module, "_get_pipeline", lambda: mock_pipeline)


@pytest.fixture(autouse=True)
def _patch_retriever_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """全テストで _get_retriever_pipeline() を差し替え、実 LLM / Neo4j 接続を回避する。

    stream() は ("reasoning", ...) × 4 + ("content", answer) のシーケンスを返す。
    """
    from origin_spyglass.api.v1 import ideas as ideas_module

    mock_pipeline = MagicMock()
    mock_pipeline.run.return_value = _SAMPLE_RETRIEVER_OUTPUT
    mock_pipeline.stream.return_value = iter(
        [
            ("reasoning", "STEP1: バリデーション完了"),
            ("reasoning", "STEP2: 意図解析完了"),
            ("reasoning", "STEP3: グラフ検索完了"),
            ("reasoning", "STEP4: 結果整形完了"),
            ("content", _SAMPLE_RETRIEVER_OUTPUT.answer),
        ]
    )
    monkeypatch.setattr(ideas_module, "_get_retriever_pipeline", lambda: mock_pipeline)


# --- 正常系 ---


def test_persist_relations_returns_201() -> None:
    response = client.post("/v1/ideas/relations", json=_VALID_PERSIST_BODY)
    assert response.status_code == 201


def test_persist_relations_returns_correct_schema() -> None:
    # レスポンスボディが IdeaRelationPersisterOutput のスキーマに準拠すること
    response = client.post("/v1/ideas/relations", json=_VALID_PERSIST_BODY)
    data = response.json()
    assert data["doc_id"] == "doc-001"
    assert data["persisted"] is True
    assert data["node_count"] == 5
    assert data["edge_count"] == 4
    assert data["elapsed_ms"] == 123
    assert data["warnings"] == []


# --- 異常系: パイプラインエラーの HTTP ステータスマッピング ---


def test_persist_relations_validation_error_returns_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # IdeaRelationValidationError → 422 Unprocessable Entity
    from origin_spyglass.api.v1 import ideas as ideas_module

    mock = MagicMock()
    mock.run.side_effect = IdeaRelationValidationError("doc_id", "empty")
    monkeypatch.setattr(ideas_module, "_get_pipeline", lambda: mock)

    response = client.post("/v1/ideas/relations", json=_VALID_PERSIST_BODY)
    assert response.status_code == 422


def test_persist_relations_graph_unavailable_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # GraphStoreUnavailable → 503 Service Unavailable
    from origin_spyglass.api.v1 import ideas as ideas_module

    mock = MagicMock()
    mock.run.side_effect = GraphStoreUnavailable("Neo4j unreachable")
    monkeypatch.setattr(ideas_module, "_get_pipeline", lambda: mock)

    response = client.post("/v1/ideas/relations", json=_VALID_PERSIST_BODY)
    assert response.status_code == 503


def test_persist_relations_extraction_failed_returns_502(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ExtractionFailed → 502 Bad Gateway（LLM への依存失敗）
    from origin_spyglass.api.v1 import ideas as ideas_module

    mock = MagicMock()
    mock.run.side_effect = ExtractionFailed("LLM timeout")
    monkeypatch.setattr(ideas_module, "_get_pipeline", lambda: mock)

    response = client.post("/v1/ideas/relations", json=_VALID_PERSIST_BODY)
    assert response.status_code == 502


def test_persist_relations_persist_failed_returns_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # PersistFailed → 500 Internal Server Error
    from origin_spyglass.api.v1 import ideas as ideas_module

    mock = MagicMock()
    mock.run.side_effect = PersistFailed("write error")
    monkeypatch.setattr(ideas_module, "_get_pipeline", lambda: mock)

    response = client.post("/v1/ideas/relations", json=_VALID_PERSIST_BODY)
    assert response.status_code == 500


def test_persist_relations_pydantic_validation_error_returns_422() -> None:
    # 必須フィールド欠落は Pydantic が自動で 422 を返す（ルーターのエラーマッピング不要）
    body = {**_VALID_PERSIST_BODY}
    del body["doc_id"]
    response = client.post("/v1/ideas/relations", json=body)
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["get", "put", "delete", "patch"])
def test_persist_relations_method_not_allowed(method: str) -> None:
    # POST 以外の HTTP メソッドは 405 Method Not Allowed
    response = getattr(client, method)("/v1/ideas/relations")
    assert response.status_code == 405


# ---------------------------------------------------------------------------
# POST /v1/ideas/relations/retrieval  (SSE streaming)
# ---------------------------------------------------------------------------


def _parse_sse_chunks(response_text: str) -> list[dict]:
    """SSE レスポンスボディから data: 行をパースして JSON オブジェクトのリストを返す。"""
    chunks = []
    for line in response_text.splitlines():
        if line.startswith("data: ") and line != "data: [DONE]":
            chunks.append(json.loads(line[len("data: ") :]))
    return chunks


def test_retrieve_relations_returns_200() -> None:
    response = client.post("/v1/ideas/relations/retrieval", json=_VALID_SEARCH_BODY)
    assert response.status_code == 200


def test_retrieve_relations_content_type_is_event_stream() -> None:
    response = client.post("/v1/ideas/relations/retrieval", json=_VALID_SEARCH_BODY)
    assert "text/event-stream" in response.headers["content-type"]


def test_retrieve_relations_stream_ends_with_done() -> None:
    response = client.post("/v1/ideas/relations/retrieval", json=_VALID_SEARCH_BODY)
    assert "data: [DONE]" in response.text


def test_retrieve_relations_stream_has_reasoning_chunks() -> None:
    response = client.post("/v1/ideas/relations/retrieval", json=_VALID_SEARCH_BODY)
    chunks = _parse_sse_chunks(response.text)
    reasoning_chunks = [
        c for c in chunks if c.get("choices", [{}])[0].get("delta", {}).get("reasoning_content")
    ]
    assert len(reasoning_chunks) >= 1


def test_retrieve_relations_stream_has_content_chunk_with_answer() -> None:
    response = client.post("/v1/ideas/relations/retrieval", json=_VALID_SEARCH_BODY)
    chunks = _parse_sse_chunks(response.text)
    content_chunks = [
        c for c in chunks if c.get("choices", [{}])[0].get("delta", {}).get("content")
    ]
    assert len(content_chunks) == 1
    assert content_chunks[0]["choices"][0]["delta"]["content"] == _SAMPLE_RETRIEVER_OUTPUT.answer


def test_retrieve_relations_stream_chunk_schema() -> None:
    response = client.post("/v1/ideas/relations/retrieval", json=_VALID_SEARCH_BODY)
    chunks = _parse_sse_chunks(response.text)
    assert len(chunks) > 0
    first = chunks[0]
    assert "id" in first
    assert first["object"] == "chat.completion.chunk"
    assert "created" in first
    assert "model" in first
    assert isinstance(first["choices"], list)


def test_retrieve_relations_validation_error_returns_422() -> None:
    # バリデーションはストリーミング開始前なので 422 を返せる
    response = client.post("/v1/ideas/relations/retrieval", json={"question": ""})
    assert response.status_code == 422


def test_retrieve_relations_pydantic_validation_error_returns_422() -> None:
    # question フィールド欠落は Pydantic が自動で 422 を返す
    response = client.post("/v1/ideas/relations/retrieval", json={})
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["get", "put", "delete", "patch"])
def test_retrieve_relations_method_not_allowed(method: str) -> None:
    response = getattr(client, method)("/v1/ideas/relations/retrieval")
    assert response.status_code == 405

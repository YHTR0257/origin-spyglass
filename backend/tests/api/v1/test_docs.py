"""GET /v1/docs / POST /v1/docs API テスト

実際の PostgreSQL への接続が不要なよう、セッション依存をモックする。
"""

from collections.abc import AsyncGenerator, Generator
from datetime import date
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from origin_spyglass.api.v1 import docs as docs_module
from origin_spyglass.doc_relationship_persister import (
    DocRelationshipPersisterOutput,
)
from origin_spyglass.main import app
from origin_spyglass.schemas.doc_relation import SourceType

_SAMPLE_OUTPUT = DocRelationshipPersisterOutput(
    doc_id="report",
    display_id="DOC-report",
    title="My Report",
    source_file="report.md",
    domain="tech",
    tags=["ai"],
    author="Alice",
    source_type=SourceType.LOCAL_MARKDOWN,
    confidence=0.9,
    date=date(2026, 4, 1),
    created_at="2026-04-14T00:00:00",
)

_VALID_BODY = {
    "document": {
        "mime": "text/markdown",
        "markdown": "# Hello\n\nBody.",
        "meta": {
            "domain": "tech",
            "tags": ["ai"],
            "title": "My Report",
            "created_at": "2026-04-14T00:00:00",
            "source_file": "report.md",
        },
    },
    "author": "Alice",
    "source_type": "local_markdown",
    "confidence": 0.9,
    "date": "2026-04-01",
}


def _mock_session() -> AsyncSession:
    return AsyncMock(spec=AsyncSession)


async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
    yield _mock_session()


@pytest.fixture(autouse=True)
def _patch_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """DocRelationshipPersisterService をモックして DB 接続を回避する"""
    from origin_spyglass.doc_relationship_persister import service as svc_module

    async def _persist(self: Any, input: Any) -> Any:
        return _SAMPLE_OUTPUT

    async def _list(self: Any, domain: Any = None, limit: int = 50, offset: int = 0) -> Any:
        return [_SAMPLE_OUTPUT]

    async def _get(self: Any, doc_id: Any) -> Any:
        if doc_id == "report":
            return _SAMPLE_OUTPUT
        return None

    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "persist", _persist)
    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "list_documents", _list)
    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "get_document", _get)

    app.dependency_overrides[docs_module._get_session] = _override_get_session


@pytest.fixture(autouse=True)
def _clear_overrides() -> Generator[None, None, None]:
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_persist_document_created() -> None:
    """POST /v1/docs が 201 と出力スキーマを返す"""
    response = client.post("/v1/docs", json=_VALID_BODY)
    assert response.status_code == 201
    data = response.json()
    assert data["doc_id"] == "report"
    assert data["display_id"] == "DOC-report"
    assert data["author"] == "Alice"
    assert data["source_type"] == "local_markdown"


def test_persist_document_invalid_schema() -> None:
    """POST /v1/docs に不正スキーマを送ると 422 が返る"""
    response = client.post("/v1/docs", json={"invalid": "data"})
    assert response.status_code == 422


def test_list_documents() -> None:
    """GET /v1/docs がドキュメント一覧を返す"""
    response = client.get("/v1/docs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["doc_id"] == "report"


def test_list_documents_with_domain_filter() -> None:
    """GET /v1/docs?domain=tech がクエリパラメータを受け付ける"""
    response = client.get("/v1/docs", params={"domain": "tech"})
    assert response.status_code == 200


def test_get_document_found() -> None:
    """GET /v1/docs/{doc_id} が存在するドキュメントを返す"""
    response = client.get("/v1/docs/report")
    assert response.status_code == 200
    assert response.json()["doc_id"] == "report"


def test_get_document_not_found() -> None:
    """GET /v1/docs/{doc_id} が存在しない doc_id に対して 404 を返す"""
    response = client.get("/v1/docs/nonexistent")
    assert response.status_code == 404


def test_persist_document_duplicate_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
    """service が DuplicateDocumentError を送出した場合に 409 が返る"""
    from origin_spyglass.doc_relationship_persister import DuplicateDocumentError
    from origin_spyglass.doc_relationship_persister import service as svc_module

    async def _raise_dup(self: Any, input: Any) -> Any:  # noqa: ANN001
        raise DuplicateDocumentError(doc_id="abc-123", title="My Report", year=2026)

    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "persist", _raise_dup)

    response = client.post("/v1/docs", json=_VALID_BODY)
    assert response.status_code == 409


def test_persist_document_metadata_error_returns_422(monkeypatch: pytest.MonkeyPatch) -> None:
    """service が MetadataValidationError を送出した場合に 422 が返る"""
    from origin_spyglass.doc_relationship_persister import MetadataValidationError
    from origin_spyglass.doc_relationship_persister import service as svc_module

    async def _raise_validation(self: Any, input: Any) -> Any:  # noqa: ANN001
        raise MetadataValidationError(field="title", reason="title must not be empty")

    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "persist", _raise_validation)

    response = client.post("/v1/docs", json=_VALID_BODY)
    assert response.status_code == 422


# ============================================================================
# Doc Retriever エンドポイント テスト
# ============================================================================


def test_retrieval_with_text_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /v1/docs/retrieval/text が成功"""
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _mock_run_text(self: Any, input: Any) -> Any:  # noqa: ANN001
        from origin_spyglass.doc_retriever import DocTextRetrieverOutput, RetrievedDoc

        return DocTextRetrieverOutput(
            question="quantum computer",
            answer="A quantum computer is...",
            related_docs=[
                RetrievedDoc(
                    node_id="doc-001",
                    title="Quantum Computing Basics",
                    body_snippet="Quantum computers use...",
                    relevance_score=0.95,
                )
            ],
            elapsed_ms=150,
        )

    monkeypatch.setattr(pipeline_module.DocRetrieverPipeline, "run_text", _mock_run_text)

    response = client.post(
        "/v1/docs/retrieval/text",
        json={
            "question": "quantum computer",
            "max_results": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "quantum computer"
    assert len(data["related_docs"]) > 0


def test_retrieval_with_text_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /v1/docs/retrieval/text の入力エラーで 422 が返る"""
    response = client.post(
        "/v1/docs/retrieval/text",
        json={
            "question": "",  # 空の質問
            "max_results": 10,
        },
    )
    # バリデーション失敗
    assert response.status_code == 422


def test_retrieval_with_keywords_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /v1/docs/retrieval/keywords が成功"""
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _mock_run_keywords(self: Any, input: Any) -> Any:  # noqa: ANN001
        from origin_spyglass.doc_retriever import DocKeywordsRetrieverOutput, RetrievedDoc

        return DocKeywordsRetrieverOutput(
            keywords=["quantum", "computer"],
            answer="Found relevant documents...",
            related_docs=[
                RetrievedDoc(
                    node_id="doc-002",
                    title="Quantum Physics",
                    body_snippet="Quantum mechanics...",
                    relevance_score=0.87,
                )
            ],
            elapsed_ms=100,
        )

    monkeypatch.setattr(pipeline_module.DocRetrieverPipeline, "run_keywords", _mock_run_keywords)

    response = client.post(
        "/v1/docs/retrieval/keywords",
        json={
            "keywords": ["quantum", "computer"],
            "max_results": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["keywords"] == ["quantum", "computer"]


def test_retrieval_with_doc_ids_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /v1/docs/retrieval/doc-ids が成功"""
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _mock_run_doc_ids(self: Any, input: Any) -> Any:  # noqa: ANN001
        from origin_spyglass.doc_retriever import DocIdsRetrieverOutput, RetrievedDoc

        return DocIdsRetrieverOutput(
            doc_ids=["550e8400-e29b-41d4-a716-446655440000"],
            answer="Retrieved document summary...",
            related_docs=[
                RetrievedDoc(
                    node_id="550e8400-e29b-41d4-a716-446655440000",
                    title="Retrieved Doc",
                    body_snippet="Document content...",
                    relevance_score=1.0,
                )
            ],
            elapsed_ms=50,
        )

    monkeypatch.setattr(pipeline_module.DocRetrieverPipeline, "run_doc_ids", _mock_run_doc_ids)

    response = client.post(
        "/v1/docs/retrieval/doc-ids",
        json={
            "doc_ids": ["550e8400-e29b-41d4-a716-446655440000"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["doc_ids"]) == 1


def test_retrieval_with_text_query_failed_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /v1/docs/retrieval/text で QueryFailed 発生時に 500 が返る"""
    from origin_spyglass.doc_retriever import QueryFailed
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _raise_query_failed(self: Any, input: Any) -> Any:  # noqa: ANN001
        raise QueryFailed("llm failed")

    monkeypatch.setattr(pipeline_module.DocRetrieverPipeline, "run_text", _raise_query_failed)

    response = client.post(
        "/v1/docs/retrieval/text",
        json={
            "question": "quantum computer",
            "max_results": 10,
        },
    )
    assert response.status_code == 500


def test_retrieval_with_keywords_vector_store_unavailable_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /v1/docs/retrieval/keywords で VectorStoreUnavailable 発生時に 503 が返る"""
    from origin_spyglass.doc_relationship_persister.types import VectorStoreUnavailable
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _raise_vector_store_unavailable(self: Any, input: Any) -> Any:  # noqa: ANN001
        raise VectorStoreUnavailable("postgres unavailable")

    monkeypatch.setattr(
        pipeline_module.DocRetrieverPipeline,
        "run_keywords",
        _raise_vector_store_unavailable,
    )

    response = client.post(
        "/v1/docs/retrieval/keywords",
        json={
            "keywords": ["quantum", "computer"],
            "max_results": 10,
        },
    )
    assert response.status_code == 503


def test_retrieval_with_text_vector_store_unavailable_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /v1/docs/retrieval/text で VectorStoreUnavailable 発生時に 503 が返る"""
    from origin_spyglass.doc_relationship_persister.types import VectorStoreUnavailable
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _raise(self: Any, input: Any) -> Any:  # noqa: ANN001
        raise VectorStoreUnavailable("postgres unavailable")

    monkeypatch.setattr(pipeline_module.DocRetrieverPipeline, "run_text", _raise)

    response = client.post(
        "/v1/docs/retrieval/text",
        json={"question": "quantum computer", "max_results": 10},
    )
    assert response.status_code == 503


def test_retrieval_with_keywords_query_failed_returns_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /v1/docs/retrieval/keywords で QueryFailed 発生時に 500 が返る"""
    from origin_spyglass.doc_retriever import QueryFailed
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _raise(self: Any, input: Any) -> Any:  # noqa: ANN001
        raise QueryFailed("query failed")

    monkeypatch.setattr(pipeline_module.DocRetrieverPipeline, "run_keywords", _raise)

    response = client.post(
        "/v1/docs/retrieval/keywords",
        json={"keywords": ["quantum", "computer"], "max_results": 10},
    )
    assert response.status_code == 500


def test_retrieval_with_doc_ids_validation_error_returns_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /v1/docs/retrieval/doc-ids で DocRetrieverValidationError 発生時に 422 が返る"""
    from origin_spyglass.doc_retriever import DocRetrieverValidationError
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _raise(self: Any, input: Any) -> Any:  # noqa: ANN001
        raise DocRetrieverValidationError("doc_ids", "1件以上必須")

    monkeypatch.setattr(pipeline_module.DocRetrieverPipeline, "run_doc_ids", _raise)

    response = client.post(
        "/v1/docs/retrieval/doc-ids",
        json={"doc_ids": ["550e8400-e29b-41d4-a716-446655440000"]},
    )
    assert response.status_code == 422


def test_retrieval_with_doc_ids_query_failed_returns_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /v1/docs/retrieval/doc-ids で QueryFailed 発生時に 500 が返る"""
    from origin_spyglass.doc_retriever import QueryFailed
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _raise(self: Any, input: Any) -> Any:  # noqa: ANN001
        raise QueryFailed("query failed")

    monkeypatch.setattr(pipeline_module.DocRetrieverPipeline, "run_doc_ids", _raise)

    response = client.post(
        "/v1/docs/retrieval/doc-ids",
        json={"doc_ids": ["550e8400-e29b-41d4-a716-446655440000"]},
    )
    assert response.status_code == 500


def test_retrieval_with_doc_ids_vector_store_unavailable_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /v1/docs/retrieval/doc-ids で VectorStoreUnavailable 発生時に 503 が返る"""
    from origin_spyglass.doc_relationship_persister.types import VectorStoreUnavailable
    from origin_spyglass.doc_retriever import pipeline as pipeline_module

    async def _raise(self: Any, input: Any) -> Any:  # noqa: ANN001
        raise VectorStoreUnavailable("postgres unavailable")

    monkeypatch.setattr(pipeline_module.DocRetrieverPipeline, "run_doc_ids", _raise)

    response = client.post(
        "/v1/docs/retrieval/doc-ids",
        json={"doc_ids": ["550e8400-e29b-41d4-a716-446655440000"]},
    )
    assert response.status_code == 503

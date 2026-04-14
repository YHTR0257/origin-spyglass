"""GET /v1/docs / POST /v1/docs API テスト

実際の PostgreSQL への接続が不要なよう、セッション依存をモックする。
"""

from collections.abc import AsyncGenerator
from datetime import date
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

    async def _persist(self, input):
        return _SAMPLE_OUTPUT

    async def _list(self, domain=None, limit=50, offset=0):
        return [_SAMPLE_OUTPUT]

    async def _get(self, doc_id):
        if doc_id == "report":
            return _SAMPLE_OUTPUT
        return None

    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "persist", _persist)
    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "list_documents", _list)
    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "get_document", _get)

    app.dependency_overrides[docs_module._get_session] = _override_get_session


@pytest.fixture(autouse=True)
def _clear_overrides():
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

    async def _raise_dup(self, input):  # noqa: ANN001
        raise DuplicateDocumentError(doc_id="abc-123", title="My Report", year=2026)

    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "persist", _raise_dup)

    response = client.post("/v1/docs", json=_VALID_BODY)
    assert response.status_code == 409


def test_persist_document_metadata_error_returns_422(monkeypatch: pytest.MonkeyPatch) -> None:
    """service が MetadataValidationError を送出した場合に 422 が返る"""
    from origin_spyglass.doc_relationship_persister import MetadataValidationError
    from origin_spyglass.doc_relationship_persister import service as svc_module

    async def _raise_validation(self, input):  # noqa: ANN001
        raise MetadataValidationError(field="title", reason="title must not be empty")

    monkeypatch.setattr(svc_module.DocRelationshipPersisterService, "persist", _raise_validation)

    response = client.post("/v1/docs", json=_VALID_BODY)
    assert response.status_code == 422

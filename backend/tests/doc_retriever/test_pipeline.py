"""パイプライン統合テスト"""

from datetime import date
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from origin_spyglass.doc_relationship_persister.types import VectorStoreUnavailable
from origin_spyglass.doc_retriever import (
    DocRetrieverValidationError,
    QueryFailed,
)
from origin_spyglass.doc_retriever.pipeline import DocRetrieverPipeline
from origin_spyglass.infra.vector_store import DocumentRecord

from ._helpers import (
    make_ids_input,
    make_keywords_input,
    make_text_input,
)


def make_mock_document() -> DocumentRecord:
    """テスト用のモック DocumentRecord を生成"""
    return DocumentRecord(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        display_id="DOC-test",
        title="Test Doc",
        source_file="test.md",
        mime="text/markdown",
        body="This is test content.",
        domain="research",
        tags=["test"],
        author="Test Author",
        source_type="local_markdown",
        confidence=0.9,
        date=date.today(),
    )


@pytest.mark.asyncio
async def test_run_text_success() -> None:
    """run_text の正常系実行"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_text = AsyncMock(return_value=[make_mock_document()])
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"interpreted_query": "optimized query"}
    )()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_text_input()

    result = await pipeline.run_text(input_data)

    assert result.question == input_data.question
    assert len(result.related_docs) > 0
    assert result.elapsed_ms >= 0


@pytest.mark.asyncio
async def test_run_text_validation_error() -> None:
    """バリデーション失敗で例外"""
    mock_manager = AsyncMock()
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_text_input(question="")

    with pytest.raises(DocRetrieverValidationError):
        await pipeline.run_text(input_data)


@pytest.mark.asyncio
async def test_run_text_query_failed() -> None:
    """クエリ失敗で例外"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_text = AsyncMock(side_effect=Exception("query error"))
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"interpreted_query": "query"}
    )()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_text_input()

    with pytest.raises(QueryFailed):
        await pipeline.run_text(input_data)


@pytest.mark.asyncio
async def test_run_keywords_success() -> None:
    """run_keywords の正常系実行"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_keywords = AsyncMock(return_value=[make_mock_document()])
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_keywords_input()

    result = await pipeline.run_keywords(input_data)

    assert result.keywords == input_data.keywords
    assert len(result.related_docs) > 0


@pytest.mark.asyncio
async def test_run_keywords_validation_error() -> None:
    """キーワードバリデーション失敗"""
    mock_manager = AsyncMock()
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_keywords_input(keywords=[])

    with pytest.raises(DocRetrieverValidationError):
        await pipeline.run_keywords(input_data)


@pytest.mark.asyncio
async def test_run_doc_ids_success() -> None:
    """run_doc_ids の正常系実行"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(return_value=[make_mock_document()])
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_ids_input()

    result = await pipeline.run_doc_ids(input_data)

    assert result.doc_ids == input_data.doc_ids
    assert len(result.related_docs) > 0


@pytest.mark.asyncio
async def test_run_doc_ids_validation_error() -> None:
    """ID検索バリデーション失敗"""
    mock_manager = AsyncMock()
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_ids_input(doc_ids=[])

    with pytest.raises(DocRetrieverValidationError):
        await pipeline.run_doc_ids(input_data)


@pytest.mark.asyncio
async def test_run_doc_ids_vector_store_unavailable() -> None:
    """VectorStore接続不可"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(side_effect=Exception("connection refused"))
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_ids_input()

    with pytest.raises(VectorStoreUnavailable):
        await pipeline.run_doc_ids(input_data)


@pytest.mark.asyncio
async def test_run_text_vector_store_unavailable() -> None:
    """run_text でVectorStore接続不可"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_text = AsyncMock(side_effect=Exception("connection refused"))
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"interpreted_query": "query"}
    )()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_text_input()

    with pytest.raises(VectorStoreUnavailable):
        await pipeline.run_text(input_data)


@pytest.mark.asyncio
async def test_run_keywords_query_failed() -> None:
    """run_keywords でクエリ失敗"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_keywords = AsyncMock(side_effect=Exception("syntax error"))
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_keywords_input()

    with pytest.raises(QueryFailed):
        await pipeline.run_keywords(input_data)


@pytest.mark.asyncio
async def test_run_keywords_vector_store_unavailable() -> None:
    """run_keywords でVectorStore接続不可"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_keywords = AsyncMock(side_effect=Exception("connection refused"))
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_keywords_input()

    with pytest.raises(VectorStoreUnavailable):
        await pipeline.run_keywords(input_data)


@pytest.mark.asyncio
async def test_run_doc_ids_query_failed() -> None:
    """run_doc_ids で非接続エラー → QueryFailed"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(side_effect=Exception("syntax error"))
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_ids_input()

    with pytest.raises(QueryFailed):
        await pipeline.run_doc_ids(input_data)

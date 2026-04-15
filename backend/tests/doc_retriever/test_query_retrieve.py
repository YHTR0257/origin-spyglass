"""STEP3: VectorStore 取得 テスト"""

from unittest.mock import AsyncMock

import pytest

from origin_spyglass.doc_relationship_persister.types import VectorStoreUnavailable
from origin_spyglass.doc_retriever import QueryFailed
from origin_spyglass.doc_retriever.query_retrieve import (
    explore_by_keywords,
    explore_by_text,
    fetch_by_ids,
)
from origin_spyglass.infra.vector_store import DocumentRecord


def make_mock_document(title: str = "Test Doc") -> DocumentRecord:
    """テスト用のモック DocumentRecord を生成"""
    from uuid import UUID

    doc = DocumentRecord(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        display_id="DOC-test",
        title=title,
        source_file="test.md",
        mime="text/markdown",
        body="This is test content",
        domain="research",
        tags=["test"],
        author="Test Author",
        source_type="local_markdown",
        confidence=0.9,
        date=__import__("datetime").date.today(),
    )
    return doc


@pytest.mark.asyncio
async def test_explore_by_text_success() -> None:
    """テキスト探索が成功"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_text = AsyncMock(return_value=[make_mock_document()])
    mock_llm_client = AsyncMock()

    result = await explore_by_text(
        question="quantum computer",
        manager=mock_manager,
        llm_client=mock_llm_client,
        max_results=10,
    )

    assert len(result) == 1
    mock_manager.retrieval_with_text.assert_called_once()


@pytest.mark.asyncio
async def test_explore_by_text_postgres_connection_error() -> None:
    """Postgres接続失敗でVectorStoreUnavailable例外"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_text = AsyncMock(side_effect=Exception("connection refused"))
    mock_llm_client = AsyncMock()

    with pytest.raises(VectorStoreUnavailable):
        await explore_by_text(
            question="quantum computer",
            manager=mock_manager,
            llm_client=mock_llm_client,
        )


@pytest.mark.asyncio
async def test_explore_by_text_query_error() -> None:
    """クエリ実行エラーでQueryFailed例外"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_text = AsyncMock(side_effect=Exception("syntax error"))
    mock_llm_client = AsyncMock()

    with pytest.raises(QueryFailed):
        await explore_by_text(
            question="quantum computer",
            manager=mock_manager,
            llm_client=mock_llm_client,
        )


@pytest.mark.asyncio
async def test_explore_by_keywords_success() -> None:
    """キーワード探索が成功"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_keywords = AsyncMock(
        return_value=[make_mock_document(), make_mock_document("Second Doc")]
    )
    mock_llm_client = AsyncMock()

    result = await explore_by_keywords(
        keywords=["quantum", "computer"],
        manager=mock_manager,
        llm_client=mock_llm_client,
        max_results=5,
    )

    assert len(result) == 2
    mock_manager.retrieval_with_keywords.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_by_ids_success() -> None:
    """IDフェッチが成功"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(return_value=[make_mock_document()])

    result = await fetch_by_ids(
        doc_ids=["550e8400-e29b-41d4-a716-446655440000"],
        manager=mock_manager,
    )

    assert len(result) == 1
    mock_manager.retrieval_with_doc_ids.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_by_ids_no_results() -> None:
    """IDフェッチで結果なし"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(return_value=[])

    result = await fetch_by_ids(
        doc_ids=["550e8400-e29b-41d4-a716-446655440000"],
        manager=mock_manager,
    )

    assert len(result) == 0


@pytest.mark.asyncio
async def test_fetch_by_ids_connection_error() -> None:
    """IDフェッチで接続エラー"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(side_effect=Exception("connection error"))

    with pytest.raises(VectorStoreUnavailable):
        await fetch_by_ids(
            doc_ids=["550e8400-e29b-41d4-a716-446655440000"],
            manager=mock_manager,
        )


@pytest.mark.asyncio
async def test_fetch_by_ids_query_error() -> None:
    """IDフェッチで非接続エラー → QueryFailed"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(side_effect=Exception("syntax error"))

    with pytest.raises(QueryFailed):
        await fetch_by_ids(
            doc_ids=["550e8400-e29b-41d4-a716-446655440000"],
            manager=mock_manager,
        )


@pytest.mark.asyncio
async def test_explore_by_keywords_connection_error() -> None:
    """キーワード探索で接続エラー → VectorStoreUnavailable"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_keywords = AsyncMock(side_effect=Exception("connection refused"))
    mock_llm_client = AsyncMock()

    with pytest.raises(VectorStoreUnavailable):
        await explore_by_keywords(
            keywords=["quantum", "computer"],
            manager=mock_manager,
            llm_client=mock_llm_client,
        )


@pytest.mark.asyncio
async def test_explore_by_keywords_query_error() -> None:
    """キーワード探索で非接続エラー → QueryFailed"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_keywords = AsyncMock(side_effect=Exception("syntax error"))
    mock_llm_client = AsyncMock()

    with pytest.raises(QueryFailed):
        await explore_by_keywords(
            keywords=["quantum", "computer"],
            manager=mock_manager,
            llm_client=mock_llm_client,
        )

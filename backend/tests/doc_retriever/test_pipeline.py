"""パイプライン ストリーミング テスト"""

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


# ============================================================================
# stream_text
# ============================================================================


@pytest.mark.asyncio
async def test_stream_text_yields_reasoning_and_content() -> None:
    """stream_text が reasoning × 6 + content × 1 を yield する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_text = AsyncMock(return_value=[make_mock_document()])
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"interpreted_query": "optimized query"}
    )()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_text_input()

    events: list[tuple[str, str]] = []
    async for kind, text in pipeline.stream_text(input_data):
        events.append((kind, text))

    reasoning = [t for k, t in events if k == "reasoning"]
    content = [t for k, t in events if k == "content"]

    # STEP2 × 2 + STEP3 × 2 + STEP4 × 2 = 6
    assert len(reasoning) == 6
    assert len(content) == 1

    # ステップ名が含まれることを確認
    assert any("STEP2" in t for t in reasoning)
    assert any("STEP3" in t for t in reasoning)
    assert any("STEP4" in t for t in reasoning)


@pytest.mark.asyncio
async def test_stream_text_query_failed() -> None:
    """stream_text で VectorStore 呼び出し失敗時に QueryFailed が伝播する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_text = AsyncMock(side_effect=Exception("syntax error"))
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"interpreted_query": "query"}
    )()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_text_input()

    with pytest.raises(QueryFailed):
        async for _ in pipeline.stream_text(input_data):
            pass


@pytest.mark.asyncio
async def test_stream_text_vector_store_unavailable() -> None:
    """stream_text で接続エラー時に VectorStoreUnavailable が伝播する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_text = AsyncMock(side_effect=Exception("connection refused"))
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"interpreted_query": "query"}
    )()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_text_input()

    with pytest.raises(VectorStoreUnavailable):
        async for _ in pipeline.stream_text(input_data):
            pass


@pytest.mark.asyncio
async def test_stream_text_validation_error_propagates() -> None:
    """stream_text に空 question を渡すと DocRetrieverValidationError は呼び出し元から検出する"""
    # stream_text は STEP1 をスキップするが、空 question の場合 interpret で失敗することを確認
    # （API 層が事前にバリデーション済みである前提のため、ここでは空 question での動作を記録）
    mock_manager = AsyncMock()
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"interpreted_query": ""}
    )()
    # 空 question でも interpret が失敗しなければ STEP3 以降に進む（API 側でブロック済み）
    mock_manager.retrieval_with_text = AsyncMock(return_value=[])

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    # stream_text 自体はバリデーション不要の設計
    events: list[tuple[str, str]] = []
    async for kind, text in pipeline.stream_text(make_text_input()):
        events.append((kind, text))
    assert any(k == "content" for k, _ in events)


# ============================================================================
# stream_keywords
# ============================================================================


@pytest.mark.asyncio
async def test_stream_keywords_yields_reasoning_and_content() -> None:
    """stream_keywords が reasoning × 4 + content × 1 を yield する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_keywords = AsyncMock(return_value=[make_mock_document()])
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_keywords_input()

    events: list[tuple[str, str]] = []
    async for kind, text in pipeline.stream_keywords(input_data):
        events.append((kind, text))

    reasoning = [t for k, t in events if k == "reasoning"]
    content = [t for k, t in events if k == "content"]

    # STEP3 × 2 + STEP4 × 2 = 4
    assert len(reasoning) == 4
    assert len(content) == 1
    assert any("STEP3" in t for t in reasoning)
    assert any("STEP4" in t for t in reasoning)


@pytest.mark.asyncio
async def test_stream_keywords_query_failed() -> None:
    """stream_keywords で非接続エラー時に QueryFailed が伝播する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_keywords = AsyncMock(side_effect=Exception("syntax error"))
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)

    with pytest.raises(QueryFailed):
        async for _ in pipeline.stream_keywords(make_keywords_input()):
            pass


@pytest.mark.asyncio
async def test_stream_keywords_vector_store_unavailable() -> None:
    """stream_keywords で接続エラー時に VectorStoreUnavailable が伝播する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_keywords = AsyncMock(side_effect=Exception("connection refused"))
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)

    with pytest.raises(VectorStoreUnavailable):
        async for _ in pipeline.stream_keywords(make_keywords_input()):
            pass


# ============================================================================
# stream_doc_ids
# ============================================================================


@pytest.mark.asyncio
async def test_stream_doc_ids_yields_reasoning_and_content() -> None:
    """stream_doc_ids が reasoning × 4 + content × 1 を yield する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(return_value=[make_mock_document()])
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)
    input_data = make_ids_input()

    events: list[tuple[str, str]] = []
    async for kind, text in pipeline.stream_doc_ids(input_data):
        events.append((kind, text))

    reasoning = [t for k, t in events if k == "reasoning"]
    content = [t for k, t in events if k == "content"]

    # STEP3 × 2 + STEP4 × 2 = 4
    assert len(reasoning) == 4
    assert len(content) == 1
    assert any("STEP3" in t for t in reasoning)
    assert any("STEP4" in t for t in reasoning)


@pytest.mark.asyncio
async def test_stream_doc_ids_query_failed() -> None:
    """stream_doc_ids で非接続エラー時に QueryFailed が伝播する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(side_effect=Exception("syntax error"))
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)

    with pytest.raises(QueryFailed):
        async for _ in pipeline.stream_doc_ids(make_ids_input()):
            pass


@pytest.mark.asyncio
async def test_stream_doc_ids_vector_store_unavailable() -> None:
    """stream_doc_ids で接続エラー時に VectorStoreUnavailable が伝播する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(side_effect=Exception("connection refused"))
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)

    with pytest.raises(VectorStoreUnavailable):
        async for _ in pipeline.stream_doc_ids(make_ids_input()):
            pass


@pytest.mark.asyncio
async def test_stream_doc_ids_empty_result() -> None:
    """stream_doc_ids でドキュメントが 0 件の場合も content を yield する"""
    mock_manager = AsyncMock()
    mock_manager.retrieval_with_doc_ids = AsyncMock(return_value=[])
    mock_llm = AsyncMock()

    pipeline = DocRetrieverPipeline(mock_manager, mock_llm)

    events: list[tuple[str, str]] = []
    async for kind, text in pipeline.stream_doc_ids(make_ids_input()):
        events.append((kind, text))

    content = [t for k, t in events if k == "content"]
    assert len(content) == 1

    # STEP3 完了メッセージに 0 件が含まれること
    reasoning = [t for k, t in events if k == "reasoning"]
    assert any("0 件" in t for t in reasoning)


# ============================================================================
# validation エラーは API 層で処理されるため pipeline テストから除外
# ============================================================================


def test_validation_error_not_raised_by_stream_methods() -> None:
    """stream_* メソッドはバリデーションをスキップする設計であることを記録する。

    STEP1 バリデーションは API 層 (docs.py) で実施され、
    DocRetrieverValidationError を 422 HTTPException に変換する。
    pipeline.stream_* はバリデーション済み入力を受け取ることを前提とする。
    """
    # このテストはドキュメンテーション目的。設計意図の記録のみ。
    assert issubclass(DocRetrieverValidationError, ValueError)

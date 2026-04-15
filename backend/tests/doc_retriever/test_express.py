"""STEP4: 結果整形 テスト"""

from datetime import date
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from origin_spyglass.doc_retriever.express import (
    _convert_to_retrieved_doc,
    express_doc_ids,
    express_keywords,
    express_text,
)
from origin_spyglass.infra.vector_store import DocumentRecord


def make_mock_document(title: str = "Test Doc", confidence: float = 0.9) -> DocumentRecord:
    """テスト用のモック DocumentRecord を生成"""
    doc = DocumentRecord(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        display_id="DOC-test",
        title=title,
        source_file="test.md",
        mime="text/markdown",
        body="This is test content for snippet extraction.",
        domain="research",
        tags=["test"],
        author="Test Author",
        source_type="local_markdown",
        confidence=confidence,
        date=date.today(),
    )
    return doc


def test_convert_to_retrieved_doc() -> None:
    """DocumentRecord から RetrievedDoc への変換"""
    doc = make_mock_document()
    result = _convert_to_retrieved_doc(doc)

    assert result.node_id == str(doc.id)
    assert result.title == "Test Doc"
    assert result.relevance_score == 0.9
    assert len(result.body_snippet) <= 303  # 最大300 + "..."


def test_convert_to_retrieved_doc_snippet_truncate() -> None:
    """body_snippet が300文字で切り詰められる"""
    long_body = "a" * 500
    doc = DocumentRecord(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        display_id="DOC-test",
        title="Test",
        source_file="test.md",
        mime="text/markdown",
        body=long_body,
        domain="research",
        tags=[],
        author="Author",
        source_type="local_markdown",
        confidence=0.8,
        date=date.today(),
    )
    result = _convert_to_retrieved_doc(doc)

    assert len(result.body_snippet) <= 303
    assert result.body_snippet.endswith("...")


@pytest.mark.asyncio
async def test_express_text_success() -> None:
    """テキスト結果整形が成功"""
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"summary": "Generated summary"}
    )()

    docs = [make_mock_document(), make_mock_document("Second Doc")]
    result = await express_text(
        question="quantum computer",
        related_docs=docs,
        llm_client=mock_llm,
        elapsed_ms=100,
    )

    assert result.question == "quantum computer"
    assert result.answer == "Generated summary"
    assert len(result.related_docs) == 2
    assert result.elapsed_ms == 100


@pytest.mark.asyncio
async def test_express_text_no_docs() -> None:
    """結果が0件の場合"""
    mock_llm = AsyncMock()

    result = await express_text(
        question="quantum computer",
        related_docs=[],
        llm_client=mock_llm,
        elapsed_ms=50,
    )

    assert result.question == "quantum computer"
    assert len(result.related_docs) == 0


@pytest.mark.asyncio
async def test_express_keywords_success() -> None:
    """キーワード結果整形が成功"""
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"summary": "Keyword summary"}
    )()

    docs = [make_mock_document()]
    result = await express_keywords(
        keywords=["quantum", "computer"],
        related_docs=docs,
        llm_client=mock_llm,
        elapsed_ms=80,
    )

    assert result.keywords == ["quantum", "computer"]
    assert len(result.related_docs) == 1
    assert result.elapsed_ms == 80


@pytest.mark.asyncio
async def test_express_doc_ids_success() -> None:
    """ID結果整形が成功"""
    mock_llm = AsyncMock()
    mock_llm.generate_response = lambda **kwargs: type(
        "obj", (object,), {"summary": "ID summary"}
    )()

    docs = [make_mock_document()]
    result = await express_doc_ids(
        doc_ids=["550e8400-e29b-41d4-a716-446655440000"],
        related_docs=docs,
        llm_client=mock_llm,
        elapsed_ms=60,
    )

    assert result.doc_ids == ["550e8400-e29b-41d4-a716-446655440000"]
    assert len(result.related_docs) == 1


@pytest.mark.asyncio
async def test_express_text_llm_failure_fallback() -> None:
    """LLM失敗時も最初のスニペットをfallbackとして返す"""
    mock_llm = AsyncMock()
    mock_llm.generate_response = AsyncMock(side_effect=Exception("LLM error"))

    docs = [make_mock_document("First Doc")]
    result = await express_text(
        question="quantum",
        related_docs=docs,
        llm_client=mock_llm,
        elapsed_ms=100,
    )

    # best-effort: 最初のドキュメントのスニペットを返す
    assert len(result.warnings) > 0
    assert "LLM summary generation failed" in result.warnings[0]


@pytest.mark.asyncio
async def test_express_keywords_llm_failure_fallback() -> None:
    """キーワード検索でLLM失敗時もスニペットをfallbackとして返す"""
    mock_llm = AsyncMock()
    mock_llm.generate_response = AsyncMock(side_effect=Exception("LLM error"))

    docs = [make_mock_document("First Doc")]
    result = await express_keywords(
        keywords=["quantum", "computer"],
        related_docs=docs,
        llm_client=mock_llm,
        elapsed_ms=80,
    )

    assert len(result.warnings) > 0
    assert "LLM summary generation failed" in result.warnings[0]


@pytest.mark.asyncio
async def test_express_doc_ids_llm_failure_fallback() -> None:
    """ID取得でLLM失敗時もスニペットをfallbackとして返す"""
    mock_llm = AsyncMock()
    mock_llm.generate_response = AsyncMock(side_effect=Exception("LLM error"))

    docs = [make_mock_document("First Doc")]
    result = await express_doc_ids(
        doc_ids=["550e8400-e29b-41d4-a716-446655440000"],
        related_docs=docs,
        llm_client=mock_llm,
        elapsed_ms=60,
    )

    assert len(result.warnings) > 0
    assert "LLM summary generation failed" in result.warnings[0]

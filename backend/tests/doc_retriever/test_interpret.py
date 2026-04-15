"""STEP2: LLM 意図解析 テスト"""

from unittest.mock import AsyncMock

import pytest

from origin_spyglass.doc_retriever import QueryFailed
from origin_spyglass.doc_retriever.interpret import interpret


@pytest.mark.asyncio
async def test_interpret_success() -> None:
    """通常の意図解析が成功"""
    mock_llm_client = AsyncMock()
    mock_llm_client.generate_response = lambda **kwargs: type(
        "obj", (object,), {"interpreted_query": "quantum computer classical comparison"}
    )()

    question = "量子コンピュータと古典コンピュータの関係は？"
    result = await interpret(question, mock_llm_client)

    assert result == "quantum computer classical comparison"


@pytest.mark.asyncio
async def test_interpret_llm_failure() -> None:
    """LLM呼び出し失敗でQueryFailed例外"""
    mock_llm_client = AsyncMock()
    mock_llm_client.generate_response = AsyncMock(side_effect=Exception("LLM connection error"))

    question = "質問文"
    with pytest.raises(QueryFailed):
        await interpret(question, mock_llm_client)


@pytest.mark.asyncio
async def test_interpret_timeout() -> None:
    """LLMタイムアウトでQueryFailed例外"""
    mock_llm_client = AsyncMock()
    mock_llm_client.generate_response = AsyncMock(side_effect=TimeoutError("LLM timeout"))

    question = "質問文"
    with pytest.raises(QueryFailed):
        await interpret(question, mock_llm_client)

"""STEP2: LLM 意図解析（text 入力のみ）"""

from typing import cast

from pydantic import BaseModel

from spyglass_utils.logging import get_logger

from ..infra.llm.base import LlamaIndexLlmClient
from .types import QueryFailed

_logger = get_logger(__name__)


class InterpretationResponse(BaseModel):
    """意図解析の応答スキーマ"""

    interpreted_query: str


async def interpret(question: str, llm_client: LlamaIndexLlmClient) -> str:
    """LLM を使用して質問を解析・最適化してベクトル検索用クエリに変換

    Args:
        question: ユーザーの質問文
        llm_client: LLM クライアント

    Returns:
        ベクトル検索向けに最適化されたクエリ文字列

    Raises:
        QueryFailed: LLM 呼び出し失敗またはパース失敗
    """
    try:
        # LLM プロンプト
        system_prompt = (
            "You are a query optimizer for semantic search. "
            "Given a user question, extract and refine keywords and concepts "
            "to optimize for vector database search. "
            "Return a concise, search-optimized query."
        )

        user_prompt = (
            f"Please analyze and optimize this question for vector search:\n"
            f"Question: {question}\n\n"
            f"Respond with ONLY the optimized query (no explanation)."
        )

        # LLM 呼び出し（構造化出力）
        response = llm_client.generate_response(
            prompt=f"{system_prompt}\n\n{user_prompt}",
            response_model=InterpretationResponse,
        )

        interpreted_query = cast(str, response.interpreted_query)
        _logger.debug(f"interpreted_query: {interpreted_query}")
        return interpreted_query
    except Exception as e:
        _logger.error(f"interpret failed: {e}")
        raise QueryFailed(f"LLM interpretation failed: {e}") from e

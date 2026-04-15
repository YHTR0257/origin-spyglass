"""STEP4: クエリ結果の整形・出力構築"""

import time
from typing import Any

from spyglass_utils.logging import get_logger

from .types import IdeaRelationRetrieverOutput, RelatedIdea

_logger = get_logger(__name__)

_BODY_SNIPPET_MAX_LENGTH = 300


def _node_to_related_idea(node_with_score: Any) -> RelatedIdea:
    """NodeWithScore を RelatedIdea に変換する。

    Args:
        node_with_score: LlamaIndex の NodeWithScore オブジェクト

    Returns:
        RelatedIdea
    """
    node = node_with_score.node  # type: ignore[attr-defined]
    score: float = node_with_score.score or 0.0  # type: ignore[attr-defined]

    node_id: str = node.node_id  # type: ignore[attr-defined]

    metadata: dict[str, Any] = getattr(node, "metadata", {}) or {}
    title: str = metadata.get("title", "")
    if not title:
        # メタデータに title がない場合は本文の先頭行を代用する
        raw_text: str = node.get_text()  # type: ignore[attr-defined]
        title = raw_text.splitlines()[0].strip() if raw_text else ""

    body_snippet: str = node.get_text()[:_BODY_SNIPPET_MAX_LENGTH]  # type: ignore[attr-defined]
    relevance_score = min(1.0, max(0.0, score))

    return RelatedIdea(
        node_id=node_id,
        title=title,
        body_snippet=body_snippet,
        relevance_score=relevance_score,
    )


def build_retriever_output(
    question: str,
    query_result: Any,
    start_ns: int,
    warnings: list[str] | None = None,
) -> IdeaRelationRetrieverOutput:
    """クエリエンジンの結果を IdeaRelationRetrieverOutput に整形する。

    ノード変換に失敗した場合は best-effort でスキップし warnings に記録する。
    関連ノードが 0 件でも正常返却する（エラーにしない）。

    Args:
        question: 元の質問文
        query_result: LlamaIndex QueryEngine のレスポンスオブジェクト
        start_ns: 処理開始時刻（time.monotonic_ns()）
        warnings: 上流から引き継ぐ警告リスト

    Returns:
        IdeaRelationRetrieverOutput
    """
    accumulated_warnings: list[str] = list(warnings or [])

    answer: str = getattr(query_result, "response", "") or ""

    related_ideas: list[RelatedIdea] = []
    source_nodes: list[Any] = getattr(query_result, "source_nodes", []) or []

    for node_with_score in source_nodes:
        try:
            related_ideas.append(_node_to_related_idea(node_with_score))
        except Exception as exc:
            _logger.warning("Failed to convert node to RelatedIdea: %s", exc)
            accumulated_warnings.append(f"node conversion failed: {exc}")

    elapsed_ms = (time.monotonic_ns() - start_ns) // 1_000_000

    return IdeaRelationRetrieverOutput(
        question=question,
        answer=answer,
        related_ideas=related_ideas,
        elapsed_ms=elapsed_ms,
        warnings=accumulated_warnings,
    )

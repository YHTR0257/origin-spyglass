"""STEP4: 結果整形"""

from typing import cast

from spyglass_utils.logging import get_logger

from ..infra.llm.base import LlamaIndexLlmClient
from ..infra.vector_store import DocumentRecord
from .types import (
    DocIdsRetrieverOutput,
    DocKeywordsRetrieverOutput,
    DocTextRetrieverOutput,
    RetrievedDoc,
)

_logger = get_logger(__name__)

_MAX_SNIPPET_LENGTH = 300


async def express_text(
    question: str,
    related_docs: list[DocumentRecord],
    llm_client: LlamaIndexLlmClient,
    elapsed_ms: int,
) -> DocTextRetrieverOutput:
    """テキスト検索結果を整形して出力スキーマに変換

    Args:
        question: 質問文
        related_docs: 検索結果のドキュメント
        llm_client: LLM クライアント（サマリー生成用）
        elapsed_ms: 処理時間（ms）

    Returns:
        出力スキーマ

    Raises:
        QueryFailed: LLM サマリー生成失敗時
    """
    warnings = []

    # ドキュメント変換
    retrieved_docs = []
    for doc in related_docs:
        try:
            retrieved_docs.append(_convert_to_retrieved_doc(doc))
        except Exception as e:
            _logger.warning(f"Failed to convert document {doc.id}: {e}")
            warnings.append(f"Document conversion failed: {str(e)}")

    # LLM によるサマリー生成
    answer = await _generate_summary(
        question=question,
        documents=retrieved_docs,
        llm_client=llm_client,
        warnings=warnings,
    )

    return DocTextRetrieverOutput(
        question=question,
        answer=answer,
        related_docs=retrieved_docs,
        elapsed_ms=elapsed_ms,
        warnings=warnings,
    )


async def express_keywords(
    keywords: list[str],
    related_docs: list[DocumentRecord],
    llm_client: LlamaIndexLlmClient,
    elapsed_ms: int,
) -> DocKeywordsRetrieverOutput:
    """キーワード検索結果を整形して出力スキーマに変換

    Args:
        keywords: キーワードリスト
        related_docs: 検索結果のドキュメント
        llm_client: LLM クライアント（サマリー生成用）
        elapsed_ms: 処理時間（ms）

    Returns:
        出力スキーマ

    Raises:
        QueryFailed: LLM サマリー生成失敗時
    """
    warnings = []

    # ドキュメント変換
    retrieved_docs = []
    for doc in related_docs:
        try:
            retrieved_docs.append(_convert_to_retrieved_doc(doc))
        except Exception as e:
            _logger.warning(f"Failed to convert document {doc.id}: {e}")
            warnings.append(f"Document conversion failed: {str(e)}")

    # LLM によるサマリー生成
    keywords_text = ", ".join(keywords)
    answer = await _generate_summary(
        question=f"Keywords: {keywords_text}",
        documents=retrieved_docs,
        llm_client=llm_client,
        warnings=warnings,
    )

    return DocKeywordsRetrieverOutput(
        keywords=keywords,
        answer=answer,
        related_docs=retrieved_docs,
        elapsed_ms=elapsed_ms,
        warnings=warnings,
    )


async def express_doc_ids(
    doc_ids: list[str],
    related_docs: list[DocumentRecord],
    llm_client: LlamaIndexLlmClient,
    elapsed_ms: int,
) -> DocIdsRetrieverOutput:
    """ID 取得結果を整形して出力スキーマに変換

    Args:
        doc_ids: ドキュメント ID リスト
        related_docs: 取得したドキュメント
        llm_client: LLM クライアント（サマリー生成用）
        elapsed_ms: 処理時間（ms）

    Returns:
        出力スキーマ

    Raises:
        QueryFailed: LLM サマリー生成失敗時
    """
    warnings = []

    # ドキュメント変換
    retrieved_docs = []
    for doc in related_docs:
        try:
            retrieved_docs.append(_convert_to_retrieved_doc(doc))
        except Exception as e:
            _logger.warning(f"Failed to convert document {doc.id}: {e}")
            warnings.append(f"Document conversion failed: {str(e)}")

    # LLM によるサマリー生成
    answer = await _generate_summary(
        question="Retrieved documents",
        documents=retrieved_docs,
        llm_client=llm_client,
        warnings=warnings,
    )

    return DocIdsRetrieverOutput(
        doc_ids=doc_ids,
        answer=answer,
        related_docs=retrieved_docs,
        elapsed_ms=elapsed_ms,
        warnings=warnings,
    )


def _convert_to_retrieved_doc(doc: DocumentRecord) -> RetrievedDoc:
    """DocumentRecord を RetrievedDoc に変換

    Args:
        doc: DocumentRecord インスタンス

    Returns:
        RetrievedDoc インスタンス
    """
    # body_snippet を制限
    snippet = doc.body[:_MAX_SNIPPET_LENGTH]
    if len(doc.body) > _MAX_SNIPPET_LENGTH:
        snippet += "..."

    return RetrievedDoc(
        node_id=str(doc.id),
        title=doc.title,
        body_snippet=snippet,
        relevance_score=doc.confidence,  # DocumentRecord の confidence をスコアに使用
    )


async def _generate_summary(
    question: str,
    documents: list[RetrievedDoc],
    llm_client: LlamaIndexLlmClient,
    warnings: list[str],
) -> str:
    """LLM を使用してドキュメント群のサマリーを生成

    Args:
        question: 質問文
        documents: RetrievedDoc リスト
        llm_client: LLM クライアント
        warnings: 警告リスト（ここに失敗時の警告を追加）

    Returns:
        生成されたサマリー（失敗時は空文字列）
    """
    try:
        if not documents:
            return "No related documents found."

        # LLM プロンプト構成
        doc_text = "\n".join([f"- {doc.title}: {doc.body_snippet}" for doc in documents[:5]])

        prompt = (
            f"Based on the following documents, provide a concise answer to the question.\n"
            f"Question: {question}\n\n"
            f"Documents:\n{doc_text}\n\n"
            f"Answer:"
        )

        # LLM 呼び出し
        from pydantic import BaseModel

        class SummaryResponse(BaseModel):
            summary: str

        response = llm_client.generate_response(
            prompt=prompt,
            response_model=SummaryResponse,
        )

        return cast(str, response.summary)
    except Exception as e:
        _logger.warning(f"Summary generation failed: {e}")
        warnings.append(f"LLM summary generation failed: {str(e)}")
        # best-effort: 最初のドキュメントのスニペットを返す
        return documents[0].body_snippet if documents else ""

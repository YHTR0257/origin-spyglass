"""STEP3: VectorStore 探索"""

from spyglass_utils.logging import get_logger

from ..doc_relationship_persister.types import VectorStoreUnavailable
from ..infra.llm.base import LlamaIndexLlmClient
from ..infra.vector_store import DocumentRecord, VectorStoreManager
from .types import QueryFailed

_logger = get_logger(__name__)


async def explore_by_text(
    question: str,
    manager: VectorStoreManager,
    llm_client: LlamaIndexLlmClient,
    max_results: int = 10,
    domain: str | None = None,
) -> list[DocumentRecord]:
    """テキストクエリでドキュメントを検索

    Args:
        question: 質問文
        manager: VectorStoreManager インスタンス
        llm_client: LLM クライアント（ベクトル化用）
        max_results: 返すドキュメントの最大数
        domain: 検索対象ドメイン（オプション）

    Returns:
        関連ドキュメントのリスト

    Raises:
        VectorStoreUnavailable: VectorStore 接続不可
        QueryFailed: クエリ実行エラー
    """
    try:
        # ベクトル化（LLM クライアントで埋め込み生成）
        # 注: 実装時に LlamaIndex の埋め込みモデルと統合
        # 暫定的には質問テキストを返す
        embedding = _generate_embedding(question, llm_client)

        # VectorStore 検索
        try:
            docs = await manager.retrieval_with_text(
                query_embedding=embedding,
                max_results=max_results,
                domain=domain,
            )
            return docs
        except Exception as e:
            _logger.error(f"retrieval_with_text failed: {e}")
            if isinstance(e, Exception) and "connection" in str(e).lower():
                raise VectorStoreUnavailable("PostgreSQL connection failed") from e
            raise QueryFailed(f"Query execution failed: {e}") from e

    except (VectorStoreUnavailable, QueryFailed):
        raise
    except Exception as e:
        _logger.error(f"explore_by_text failed: {e}")
        raise QueryFailed(f"Exploration failed: {e}") from e


async def explore_by_keywords(
    keywords: list[str],
    manager: VectorStoreManager,
    llm_client: LlamaIndexLlmClient,
    max_results: int = 10,
    domain: str | None = None,
) -> list[DocumentRecord]:
    """キーワードリストでドキュメントを検索

    Args:
        keywords: キーワードのリスト
        manager: VectorStoreManager インスタンス
        llm_client: LLM クライアント（ベクトル化用）
        max_results: 返すドキュメントの最大数
        domain: 検索対象ドメイン（オプション）

    Returns:
        関連ドキュメントのリスト

    Raises:
        VectorStoreUnavailable: VectorStore 接続不可
        QueryFailed: クエリ実行エラー
    """
    try:
        # キーワードを結合してベクトル化
        keywords_text = " ".join(keywords)
        embedding = _generate_embedding(keywords_text, llm_client)

        # VectorStore 検索
        try:
            docs = await manager.retrieval_with_keywords(
                keyword_embedding=embedding,
                max_results=max_results,
                domain=domain,
            )
            return docs
        except Exception as e:
            _logger.error(f"retrieval_with_keywords failed: {e}")
            if isinstance(e, Exception) and "connection" in str(e).lower():
                raise VectorStoreUnavailable("PostgreSQL connection failed") from e
            raise QueryFailed(f"Query execution failed: {e}") from e

    except (VectorStoreUnavailable, QueryFailed):
        raise
    except Exception as e:
        _logger.error(f"explore_by_keywords failed: {e}")
        raise QueryFailed(f"Exploration failed: {e}") from e


async def fetch_by_ids(
    doc_ids: list[str],
    manager: VectorStoreManager,
) -> list[DocumentRecord]:
    """ドキュメント ID リストから直接ドキュメントを取得

    Args:
        doc_ids: ドキュメント ID のリスト
        manager: VectorStoreManager インスタンス

    Returns:
        取得したドキュメントのリスト

    Raises:
        VectorStoreUnavailable: VectorStore 接続不可
        QueryFailed: クエリ実行エラー
    """
    try:
        try:
            docs = await manager.retrieval_with_doc_ids(doc_ids)
            return docs
        except Exception as e:
            _logger.error(f"retrieval_with_doc_ids failed: {e}")
            if isinstance(e, Exception) and "connection" in str(e).lower():
                raise VectorStoreUnavailable("PostgreSQL connection failed") from e
            raise QueryFailed(f"Query execution failed: {e}") from e

    except (VectorStoreUnavailable, QueryFailed):
        raise
    except Exception as e:
        _logger.error(f"fetch_by_ids failed: {e}")
        raise QueryFailed(f"Fetch failed: {e}") from e


def _generate_embedding(text: str, llm_client: LlamaIndexLlmClient) -> list[float]:
    """テキストをベクトル埋め込みに変換

    Args:
        text: テキスト
        llm_client: LLM クライアント

    Returns:
        ベクトル埋め込み（暫定実装では固定値を返す）

    Note:
        実装時に LlamaIndex の埋め込みモデルと統合
        ここでは placeholder として固定長のベクトルを返す
    """
    # 暫定実装: 1536 次元のゼロベクトル（OpenAI embedding-3-small）
    # 実装時に LlamaIndex の VectorStoreIndex ベクトル化と統合
    return [0.0] * 1536

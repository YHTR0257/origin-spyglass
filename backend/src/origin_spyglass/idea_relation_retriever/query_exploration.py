"""STEP3: Neo4j グラフクエリ探索（retrieval_with_text() の薄いラッパー）"""

from typing import Any

from llama_index.core.llms import LLM  # type: ignore[import-untyped]

from origin_spyglass.idea_relation_persister.types import GraphStoreUnavailable
from origin_spyglass.infra.graph_store import Neo4jGraphStoreManager

from .types import QueryFailed


def explore_graph(
    query_text: str,
    store_manager: Neo4jGraphStoreManager,
    llm: LLM,
    max_results: int,
) -> Any:
    """グラフストアに対してテキストクエリを実行し、結果を返す。

    Neo4j の接続確認を先行して行い、失敗時は GraphStoreUnavailable を raise する。
    クエリ実行中の例外は QueryFailed に変換する。

    Args:
        query_text: グラフ検索に使うクエリ文字列
        store_manager: Neo4jGraphStoreManager インスタンス
        llm: LlamaIndex LLM インスタンス（クエリエンジン内部で使用）
        max_results: 返す関連ノードの最大件数

    Returns:
        LlamaIndex QueryEngine のレスポンスオブジェクト

    Raises:
        GraphStoreUnavailable: Neo4j 接続不可時
        QueryFailed: クエリ実行中の例外発生時
    """
    if not store_manager.health_check():
        raise GraphStoreUnavailable("Neo4j is unavailable")

    try:
        return store_manager.retrieval_with_text(
            query_text,
            llm=llm,
            max_results=max_results,
        )
    except GraphStoreUnavailable:
        raise
    except Exception as exc:
        raise QueryFailed(f"Graph query execution failed: {exc}") from exc

"""STEP4: Neo4j 永続化"""

from llama_index.core import Document, PropertyGraphIndex  # type: ignore[import-untyped]
from llama_index.core.llms import LLM  # type: ignore[import-untyped]
from llama_index.core.schema import TextNode  # type: ignore[import-untyped]

from origin_spyglass.infra.graph_store import Neo4jGraphStoreManager, PropertyGraphStore
from spyglass_utils.logging import get_logger

from .types import GraphStoreUnavailable, PersistFailed, ValidatedIdeaRelationInput

_logger = get_logger(__name__)


def _stamp_doc_id(nodes: list[TextNode], doc_id: str) -> None:
    """全ノードの metadata に doc_id を付与する（逆引き用）。"""
    for node in nodes:
        node.metadata["doc_id"] = doc_id


def persist_to_graph(
    nodes: list[TextNode],
    input: ValidatedIdeaRelationInput,
    store_manager: Neo4jGraphStoreManager,
    llm: LLM,
) -> PropertyGraphIndex:
    """STEP4: 抽出済みノード・エッジを Neo4j に upsert する。

    LlamaIndex の Neo4j ストアは内部で MERGE 構文を使用するため、
    同一入力の再実行は冪等に動作する。

    Args:
        nodes: STEP3 でトリプレットが付与された TextNode リスト
        input: バリデーション済み入力
        store_manager: Neo4jGraphStoreManager インスタンス
        llm: LlamaIndex LLM インスタンス（PropertyGraphIndex に渡す）

    Returns:
        書き込み済みの PropertyGraphIndex

    Raises:
        GraphStoreUnavailable: Neo4j に接続できない場合
        PersistFailed: upsert 操作が失敗した場合
    """
    if not store_manager.health_check():
        raise GraphStoreUnavailable("Neo4j is not reachable")

    _stamp_doc_id(nodes, input.doc_id)

    docs = [
        Document(
            text=node.get_content(),
            metadata=node.metadata,
        )
        for node in nodes
    ]

    try:
        pg_store = PropertyGraphStore(store_manager)
        index = PropertyGraphIndex.from_documents(
            docs,
            property_graph_store=pg_store.graph_store,
            llm=llm,
            show_progress=input.show_progress,
        )
        return index
    except GraphStoreUnavailable:
        raise
    except Exception as exc:
        _logger.error("Neo4j persist failed: %s", exc)
        raise PersistFailed(f"Neo4j upsert failed: {exc}") from exc

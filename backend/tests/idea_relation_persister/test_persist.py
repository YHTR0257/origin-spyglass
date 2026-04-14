"""STEP4: Neo4j 永続化のテスト

Neo4j への実接続は持たないため、store_manager を patch で差し替える。
- store_manager.health_check() の戻り値で GraphStoreUnavailable 分岐を制御する
- store_manager.index_documents() を patch して実 Neo4j 書き込みを回避する
"""

from unittest.mock import MagicMock

import pytest

from origin_spyglass.idea_relation_persister.persist import persist_to_graph
from origin_spyglass.idea_relation_persister.types import GraphStoreUnavailable, PersistFailed

from ._helpers import make_valid_input

try:
    from llama_index.core.schema import TextNode  # type: ignore[import-untyped]
except Exception:
    # llama-index が環境にない場合は MagicMock で代替する
    TextNode = None  # type: ignore[assignment,misc]


def _make_nodes() -> list:  # type: ignore[type-arg]
    if TextNode is None:
        return [MagicMock(metadata={}, get_content=MagicMock(return_value="text"))]
    return [TextNode(text="Alice knows Bob.", metadata={})]


def _make_store_manager(healthy: bool = True) -> MagicMock:
    """health_check() の戻り値を制御できる Neo4jGraphStoreManager モックを返す。"""
    m = MagicMock()
    m.health_check.return_value = healthy
    m.store = MagicMock()
    m.index_documents = MagicMock()
    return m


def test_persist_raises_graph_store_unavailable_when_unhealthy() -> None:
    # health_check() が False を返すと PropertyGraphIndex を呼ぶ前に失敗する
    nodes = _make_nodes()
    manager = _make_store_manager(healthy=False)
    kg_extractor = MagicMock()
    with pytest.raises(GraphStoreUnavailable):
        persist_to_graph(nodes, make_valid_input(), manager, MagicMock(), kg_extractor)


def test_persist_stamps_doc_id_on_nodes() -> None:
    # STEP4 が各ノードの metadata に doc_id を書き込むことを確認（Neo4j 逆引き用）
    nodes = _make_nodes()
    manager = _make_store_manager(healthy=True)
    kg_extractor = MagicMock()

    manager.index_documents.return_value = MagicMock()
    persist_to_graph(nodes, make_valid_input(), manager, MagicMock(), kg_extractor)

    for node in nodes:
        assert node.metadata.get("doc_id") == "doc-001"


def test_persist_calls_index_documents() -> None:
    # manager.index_documents() が一度だけ呼ばれ、返値がそのまま返ること
    nodes = _make_nodes()
    manager = _make_store_manager(healthy=True)
    kg_extractor = MagicMock()
    mock_index = MagicMock()

    manager.index_documents.return_value = mock_index
    result = persist_to_graph(nodes, make_valid_input(), manager, MagicMock(), kg_extractor)

    assert result is mock_index
    manager.index_documents.assert_called_once()
    assert manager.index_documents.call_args.kwargs["kg_extractors"] == [kg_extractor]


def test_persist_raises_persist_failed_on_exception() -> None:
    # manager.index_documents() が例外を raise した場合は PersistFailed に変換される
    nodes = _make_nodes()
    manager = _make_store_manager(healthy=True)
    kg_extractor = MagicMock()

    manager.index_documents.side_effect = RuntimeError("write error")
    with pytest.raises(PersistFailed):
        persist_to_graph(nodes, make_valid_input(), manager, MagicMock(), kg_extractor)

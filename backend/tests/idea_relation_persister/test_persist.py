"""STEP4: Neo4j 永続化のテスト

Neo4j への実接続は持たないため、store_manager と PropertyGraphIndex を patch で差し替える。
- store_manager.health_check() の戻り値で GraphStoreUnavailable 分岐を制御する
- PropertyGraphIndex.from_documents() を patch して実 Neo4j 書き込みを回避する
"""

from unittest.mock import MagicMock, patch

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
    return m


def test_persist_raises_graph_store_unavailable_when_unhealthy() -> None:
    # health_check() が False を返すと PropertyGraphIndex を呼ぶ前に失敗する
    nodes = _make_nodes()
    manager = _make_store_manager(healthy=False)
    with pytest.raises(GraphStoreUnavailable):
        persist_to_graph(nodes, make_valid_input(), manager, MagicMock())


def test_persist_stamps_doc_id_on_nodes() -> None:
    # STEP4 が各ノードの metadata に doc_id を書き込むことを確認（Neo4j 逆引き用）
    nodes = _make_nodes()
    manager = _make_store_manager(healthy=True)

    with patch("origin_spyglass.idea_relation_persister.persist.PropertyGraphIndex") as MockIndex:
        MockIndex.from_documents.return_value = MagicMock()
        with patch("origin_spyglass.idea_relation_persister.persist.PropertyGraphStore"):
            persist_to_graph(nodes, make_valid_input(), manager, MagicMock())

    for node in nodes:
        assert node.metadata.get("doc_id") == "doc-001"


def test_persist_calls_from_documents() -> None:
    # PropertyGraphIndex.from_documents() が一度だけ呼ばれ、返値がそのまま返ること
    nodes = _make_nodes()
    manager = _make_store_manager(healthy=True)
    mock_index = MagicMock()

    with patch("origin_spyglass.idea_relation_persister.persist.PropertyGraphIndex") as MockIndex:
        MockIndex.from_documents.return_value = mock_index
        with patch("origin_spyglass.idea_relation_persister.persist.PropertyGraphStore"):
            result = persist_to_graph(nodes, make_valid_input(), manager, MagicMock())

    assert result is mock_index
    MockIndex.from_documents.assert_called_once()


def test_persist_raises_persist_failed_on_exception() -> None:
    # from_documents() が例外を raise した場合は PersistFailed に変換される
    nodes = _make_nodes()
    manager = _make_store_manager(healthy=True)

    with patch("origin_spyglass.idea_relation_persister.persist.PropertyGraphIndex") as MockIndex:
        MockIndex.from_documents.side_effect = RuntimeError("write error")
        with patch("origin_spyglass.idea_relation_persister.persist.PropertyGraphStore"):
            with pytest.raises(PersistFailed):
                persist_to_graph(nodes, make_valid_input(), manager, MagicMock())

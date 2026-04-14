"""infra/graph_store.py のユニットテスト。"""

from unittest.mock import MagicMock, PropertyMock, patch

from origin_spyglass.infra.graph_store import Neo4jGraphStoreManager


def test_manager_index_documents_sets_cached_index() -> None:
    manager = Neo4jGraphStoreManager(url="bolt://x", username="u", password="p")
    llm = MagicMock()
    mock_index = MagicMock()

    with (
        patch.object(Neo4jGraphStoreManager, "store", new_callable=PropertyMock),
        patch("origin_spyglass.infra.graph_store.PropertyGraphIndex") as MockIndex,
    ):
        MockIndex.from_documents.return_value = mock_index
        result = manager.index_documents(
            [],
            llm=llm,
            kg_extractors=[MagicMock()],
            show_progress=True,
        )

    assert result is mock_index
    assert manager._index is mock_index
    MockIndex.from_documents.assert_called_once()


def test_manager_get_index_uses_cache() -> None:
    manager = Neo4jGraphStoreManager(url="bolt://x", username="u", password="p")
    llm = MagicMock()
    mock_index = MagicMock()

    with (
        patch.object(Neo4jGraphStoreManager, "store", new_callable=PropertyMock),
        patch("origin_spyglass.infra.graph_store.PropertyGraphIndex") as MockIndex,
    ):
        MockIndex.from_existing.return_value = mock_index
        first = manager.get_index(llm=llm)
        second = manager.get_index(llm=llm)

    assert first is mock_index
    assert second is mock_index
    MockIndex.from_existing.assert_called_once()


def test_retrieval_with_text_uses_query_engine_options() -> None:
    manager = Neo4jGraphStoreManager(url="bolt://x", username="u", password="p")
    llm = MagicMock()
    query_engine = MagicMock()
    query_engine.query.return_value = "ok"

    manager._index = MagicMock()
    manager._index.as_query_engine.return_value = query_engine

    result = manager.retrieval_with_text("hello", llm=llm, max_results=7)

    assert result == "ok"
    manager._index.as_query_engine.assert_called_once_with(
        include_text=True,
        similarity_top_k=7,
        sub_retrievers=["vector", "synonym"],
        llm=llm,
    )
    query_engine.query.assert_called_once_with("hello")


def test_crud_methods_delegate_to_query() -> None:
    manager = Neo4jGraphStoreManager(url="bolt://x", username="u", password="p")

    with patch.object(manager, "query", return_value=[{"ok": True}]) as mock_query:
        assert manager.create("CREATE") == [{"ok": True}]
        assert manager.read("MATCH") == [{"ok": True}]
        assert manager.update("SET") == [{"ok": True}]
        assert manager.delete("DELETE") == [{"ok": True}]

    assert mock_query.call_count == 4

"""query_exploration.py のテスト"""

from unittest.mock import MagicMock

import pytest

from origin_spyglass.idea_relation_persister.types import GraphStoreUnavailable
from origin_spyglass.idea_relation_retriever.query_exploration import explore_graph
from origin_spyglass.idea_relation_retriever.types import QueryFailed


class TestExploreGraph:
    def _make_store_manager(self, health: bool = True) -> MagicMock:
        manager = MagicMock()
        manager.health_check.return_value = health
        return manager

    def test_returns_query_result_on_success(self) -> None:
        manager = self._make_store_manager(health=True)
        expected_result = MagicMock()
        manager.retrieval_with_text.return_value = expected_result
        llm = MagicMock()

        result = explore_graph("量子コンピュータ", manager, llm, max_results=5)

        assert result is expected_result
        manager.retrieval_with_text.assert_called_once_with(
            "量子コンピュータ",
            llm=llm,
            max_results=5,
        )

    def test_health_check_false_raises_graph_store_unavailable(self) -> None:
        manager = self._make_store_manager(health=False)
        llm = MagicMock()

        with pytest.raises(GraphStoreUnavailable):
            explore_graph("クエリ", manager, llm, max_results=10)

        manager.retrieval_with_text.assert_not_called()

    def test_retrieval_exception_raises_query_failed(self) -> None:
        manager = self._make_store_manager(health=True)
        manager.retrieval_with_text.side_effect = RuntimeError("Neo4j error")
        llm = MagicMock()

        with pytest.raises(QueryFailed):
            explore_graph("クエリ", manager, llm, max_results=10)

    def test_query_failed_wraps_original_exception(self) -> None:
        original_error = ValueError("parse error")
        manager = self._make_store_manager(health=True)
        manager.retrieval_with_text.side_effect = original_error
        llm = MagicMock()

        with pytest.raises(QueryFailed) as exc_info:
            explore_graph("クエリ", manager, llm, max_results=10)

        assert exc_info.value.__cause__ is original_error

    def test_graph_store_unavailable_from_retrieval_reraises(self) -> None:
        """
        retrieval_with_text() が GraphStoreUnavailable を
        raise した場合は QueryFailed に変換しない。
        """
        manager = self._make_store_manager(health=True)
        manager.retrieval_with_text.side_effect = GraphStoreUnavailable("connection lost mid-query")
        llm = MagicMock()

        with pytest.raises(GraphStoreUnavailable):
            explore_graph("クエリ", manager, llm, max_results=10)

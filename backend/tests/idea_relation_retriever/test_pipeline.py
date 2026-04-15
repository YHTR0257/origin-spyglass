"""pipeline.py のテスト"""

from unittest.mock import MagicMock, patch

import pytest

from origin_spyglass.idea_relation_persister.types import GraphStoreUnavailable
from origin_spyglass.idea_relation_retriever.pipeline import IdeaRelationRetrieverPipeline
from origin_spyglass.idea_relation_retriever.types import (
    IdeaRelationRetrieverValidationError,
    QueryFailed,
)

from ._helpers import make_valid_input, make_valid_output

_MODULE = "origin_spyglass.idea_relation_retriever.pipeline"


class TestIdeaRelationRetrieverPipeline:
    def _make_pipeline(self) -> IdeaRelationRetrieverPipeline:
        return IdeaRelationRetrieverPipeline(
            store_manager=MagicMock(),
            llm=MagicMock(),
        )

    def test_run_executes_steps_in_order(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input()
        expected_output = make_valid_output()

        with (
            patch(f"{_MODULE}.validate", return_value=input_) as mock_validate,
            patch(
                f"{_MODULE}.interpret_question", return_value="interpreted query"
            ) as mock_interpret,
            patch(f"{_MODULE}.explore_graph", return_value=MagicMock()) as mock_explore,
            patch(
                f"{_MODULE}.build_retriever_output", return_value=expected_output
            ) as mock_express,
        ):
            result = pipeline.run(input_)

        mock_validate.assert_called_once_with(input_)
        mock_interpret.assert_called_once()
        mock_explore.assert_called_once()
        mock_express.assert_called_once()
        assert result is expected_output

    def test_validation_failure_stops_pipeline(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input()

        with (
            patch(
                f"{_MODULE}.validate",
                side_effect=IdeaRelationRetrieverValidationError("question", "empty"),
            ),
            patch(f"{_MODULE}.interpret_question") as mock_interpret,
            patch(f"{_MODULE}.explore_graph") as mock_explore,
        ):
            with pytest.raises(IdeaRelationRetrieverValidationError):
                pipeline.run(input_)

        mock_interpret.assert_not_called()
        mock_explore.assert_not_called()

    def test_interpret_failure_stops_pipeline(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input()

        with (
            patch(f"{_MODULE}.validate", return_value=input_),
            patch(f"{_MODULE}.interpret_question", side_effect=QueryFailed("LLM timeout")),
            patch(f"{_MODULE}.explore_graph") as mock_explore,
            patch(f"{_MODULE}.build_retriever_output") as mock_express,
        ):
            with pytest.raises(QueryFailed):
                pipeline.run(input_)

        mock_explore.assert_not_called()
        mock_express.assert_not_called()

    def test_explore_failure_stops_pipeline(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input()

        with (
            patch(f"{_MODULE}.validate", return_value=input_),
            patch(f"{_MODULE}.interpret_question", return_value="query"),
            patch(f"{_MODULE}.explore_graph", side_effect=GraphStoreUnavailable("Neo4j down")),
            patch(f"{_MODULE}.build_retriever_output") as mock_express,
        ):
            with pytest.raises(GraphStoreUnavailable):
                pipeline.run(input_)

        mock_express.assert_not_called()

    def test_interpreted_query_passed_to_explore(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input()

        with (
            patch(f"{_MODULE}.validate", return_value=input_),
            patch(f"{_MODULE}.interpret_question", return_value="精製されたクエリ"),
            patch(f"{_MODULE}.explore_graph", return_value=MagicMock()) as mock_explore,
            patch(f"{_MODULE}.build_retriever_output", return_value=make_valid_output()),
        ):
            pipeline.run(input_)

        actual_query_text = mock_explore.call_args[0][0]
        assert actual_query_text == "精製されたクエリ"

    def test_domain_passed_to_interpret(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input(domain="物理学")

        with (
            patch(f"{_MODULE}.validate", return_value=input_),
            patch(f"{_MODULE}.interpret_question", return_value="query") as mock_interpret,
            patch(f"{_MODULE}.explore_graph", return_value=MagicMock()),
            patch(f"{_MODULE}.build_retriever_output", return_value=make_valid_output()),
        ):
            pipeline.run(input_)

        _, kwargs = mock_interpret.call_args
        assert kwargs.get("domain") == "物理学"


class TestIdeaRelationRetrieverPipelineStream:
    def _make_pipeline(self) -> IdeaRelationRetrieverPipeline:
        return IdeaRelationRetrieverPipeline(
            store_manager=MagicMock(),
            llm=MagicMock(),
        )

    def test_stream_yields_reasoning_for_each_step(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input()
        mock_query_result = MagicMock()
        mock_query_result.source_nodes = []

        with (
            patch(f"{_MODULE}.interpret_question", return_value="精製されたクエリ"),
            patch(f"{_MODULE}.explore_graph", return_value=mock_query_result),
            patch(f"{_MODULE}.build_retriever_output", return_value=make_valid_output()),
        ):
            events = list(pipeline.stream(input_))

        kinds = [kind for kind, _ in events]
        assert kinds.count("reasoning") >= 4
        assert kinds[-1] == "content"

    def test_stream_yields_step1_reasoning_first(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input()
        mock_query_result = MagicMock()
        mock_query_result.source_nodes = []

        with (
            patch(f"{_MODULE}.interpret_question", return_value="query"),
            patch(f"{_MODULE}.explore_graph", return_value=mock_query_result),
            patch(f"{_MODULE}.build_retriever_output", return_value=make_valid_output()),
        ):
            first_kind, first_text = next(iter(pipeline.stream(input_)))

        assert first_kind == "reasoning"
        assert "STEP1" in first_text

    def test_stream_final_content_is_answer(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input()
        mock_query_result = MagicMock()
        mock_query_result.source_nodes = []
        expected_output = make_valid_output(answer="期待される回答文")

        with (
            patch(f"{_MODULE}.interpret_question", return_value="query"),
            patch(f"{_MODULE}.explore_graph", return_value=mock_query_result),
            patch(f"{_MODULE}.build_retriever_output", return_value=expected_output),
        ):
            events = list(pipeline.stream(input_))

        last_kind, last_text = events[-1]
        assert last_kind == "content"
        assert last_text == "期待される回答文"

    def test_stream_propagates_query_failed(self) -> None:
        pipeline = self._make_pipeline()
        input_ = make_valid_input()

        with (
            patch(f"{_MODULE}.interpret_question", side_effect=QueryFailed("LLM timeout")),
        ):
            with pytest.raises(QueryFailed):
                list(pipeline.stream(input_))

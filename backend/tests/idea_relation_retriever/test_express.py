"""express.py のテスト"""

import time
from unittest.mock import MagicMock

from origin_spyglass.idea_relation_retriever.express import build_retriever_output
from origin_spyglass.idea_relation_retriever.types import IdeaRelationRetrieverOutput


def _make_node_with_score(
    node_id: str = "node-001",
    text: str = "量子コンピュータは量子力学の原理を利用する。",
    metadata: dict | None = None,
    score: float = 0.92,
) -> MagicMock:
    node = MagicMock()
    node.node_id = node_id
    node.get_text.return_value = text
    node.metadata = metadata if metadata is not None else {"title": "量子コンピュータ"}
    node_with_score = MagicMock()
    node_with_score.node = node
    node_with_score.score = score
    return node_with_score


def _make_query_result(
    response: str = "量子コンピュータは古典コンピュータとは異なる計算原理を持ちます。",
    source_nodes: list | None = None,
) -> MagicMock:
    result = MagicMock()
    result.response = response
    result.source_nodes = source_nodes if source_nodes is not None else []
    return result


class TestBuildRetrieverOutput:
    def test_answer_is_populated_from_response(self) -> None:
        query_result = _make_query_result(response="回答文")
        output = build_retriever_output("質問", query_result, time.monotonic_ns())
        assert output.answer == "回答文"

    def test_question_is_preserved(self) -> None:
        query_result = _make_query_result()
        output = build_retriever_output("元の質問", query_result, time.monotonic_ns())
        assert output.question == "元の質問"

    def test_source_nodes_converted_to_related_ideas(self) -> None:
        node = _make_node_with_score(
            node_id="node-001", metadata={"title": "量子コンピュータ"}, score=0.9
        )
        query_result = _make_query_result(source_nodes=[node])

        output = build_retriever_output("質問", query_result, time.monotonic_ns())

        assert len(output.related_ideas) == 1
        idea = output.related_ideas[0]
        assert idea.node_id == "node-001"
        assert idea.title == "量子コンピュータ"
        assert idea.relevance_score == 0.9

    def test_title_falls_back_to_first_line_when_metadata_has_no_title(self) -> None:
        node = _make_node_with_score(
            text="先頭行がタイトル代わり\n2行目の内容",
            metadata={},
        )
        query_result = _make_query_result(source_nodes=[node])

        output = build_retriever_output("質問", query_result, time.monotonic_ns())

        assert output.related_ideas[0].title == "先頭行がタイトル代わり"

    def test_body_snippet_is_truncated_to_300_chars(self) -> None:
        long_text = "あ" * 500
        node = _make_node_with_score(text=long_text)
        query_result = _make_query_result(source_nodes=[node])

        output = build_retriever_output("質問", query_result, time.monotonic_ns())

        assert len(output.related_ideas[0].body_snippet) == 300

    def test_relevance_score_clamped_to_zero_on_none(self) -> None:
        node = _make_node_with_score(score=None)  # type: ignore[arg-type]
        node.score = None
        query_result = _make_query_result(source_nodes=[node])

        output = build_retriever_output("質問", query_result, time.monotonic_ns())

        assert output.related_ideas[0].relevance_score == 0.0

    def test_relevance_score_clamped_to_one_when_above_one(self) -> None:
        node = _make_node_with_score(score=1.5)
        query_result = _make_query_result(source_nodes=[node])

        output = build_retriever_output("質問", query_result, time.monotonic_ns())

        assert output.related_ideas[0].relevance_score == 1.0

    def test_empty_source_nodes_returns_empty_list(self) -> None:
        query_result = _make_query_result(source_nodes=[])
        output = build_retriever_output("質問", query_result, time.monotonic_ns())
        assert output.related_ideas == []
        assert isinstance(output, IdeaRelationRetrieverOutput)

    def test_node_conversion_failure_adds_warning_and_skips(self) -> None:
        broken_node = MagicMock()
        broken_node.node = MagicMock()
        broken_node.node.node_id = "broken"
        broken_node.node.get_text.side_effect = RuntimeError("unexpected error")
        broken_node.score = 0.5

        query_result = _make_query_result(source_nodes=[broken_node])
        output = build_retriever_output("質問", query_result, time.monotonic_ns())

        assert output.related_ideas == []
        assert len(output.warnings) == 1
        assert "node conversion failed" in output.warnings[0]

    def test_elapsed_ms_is_positive(self) -> None:
        start_ns = time.monotonic_ns()
        query_result = _make_query_result()
        output = build_retriever_output("質問", query_result, start_ns)
        assert output.elapsed_ms >= 0

    def test_upstream_warnings_are_preserved(self) -> None:
        query_result = _make_query_result()
        output = build_retriever_output(
            "質問", query_result, time.monotonic_ns(), warnings=["upstream warning"]
        )
        assert "upstream warning" in output.warnings

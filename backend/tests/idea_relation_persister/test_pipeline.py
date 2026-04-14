"""パイプラインのオーケストレーションテスト

IdeaRelationPersisterPipeline.run() が各ステップ関数を正しい順序で呼び、
エラーをそのまま伝播させることを確認する。
各ステップ関数は個別テストで検証済みなので、ここでは patch してインターフェースのみを確認する。
"""

from unittest.mock import MagicMock, patch

import pytest

from origin_spyglass.idea_relation_persister.pipeline import IdeaRelationPersisterPipeline
from origin_spyglass.idea_relation_persister.types import (
    ExtractionFailed,
    GraphStoreUnavailable,
    IdeaRelationValidationError,
    PersistFailed,
)

from ._helpers import make_valid_input, make_valid_output


def _make_pipeline() -> IdeaRelationPersisterPipeline:
    """store_manager と llm を MagicMock で注入したパイプラインを返す。"""
    return IdeaRelationPersisterPipeline(
        store_manager=MagicMock(),
        llm=MagicMock(),
    )


def test_pipeline_run_calls_all_steps() -> None:
    # STEP1〜5 が全て呼ばれること（validate → structure → extract → persist → express の順）を確認
    pipeline = _make_pipeline()
    input_ = make_valid_input()

    with (
        patch("origin_spyglass.idea_relation_persister.pipeline.validate") as mock_validate,
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.structure_document"
        ) as mock_structure,
        patch("origin_spyglass.idea_relation_persister.pipeline.extract_triplets") as mock_extract,
        patch("origin_spyglass.idea_relation_persister.pipeline.persist_to_graph") as mock_persist,
        patch("origin_spyglass.idea_relation_persister.pipeline.build_output") as mock_express,
    ):
        mock_validate.return_value = input_
        mock_structure.return_value = []
        mock_extract.return_value = []
        mock_persist.return_value = MagicMock()
        mock_express.return_value = make_valid_output()

        result = pipeline.run(input_)

    mock_validate.assert_called_once_with(input_)
    mock_structure.assert_called_once()
    mock_extract.assert_called_once()
    mock_persist.assert_called_once()
    mock_express.assert_called_once()
    assert result.doc_id == "doc-001"


def test_pipeline_run_returns_output() -> None:
    # build_output() の戻り値がそのまま run() の戻り値になること
    pipeline = _make_pipeline()
    expected = make_valid_output()

    with (
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.validate",
            return_value=make_valid_input(),
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.structure_document",
            return_value=[],
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.extract_triplets",
            return_value=[],
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.persist_to_graph",
            return_value=MagicMock(),
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.build_output",
            return_value=expected,
        ),
    ):
        result = pipeline.run(make_valid_input())

    assert result is expected


def test_pipeline_propagates_validation_error() -> None:
    # IdeaRelationValidationError は run() から伝播する（ルーターが 422 にマップする）
    pipeline = _make_pipeline()

    with patch(
        "origin_spyglass.idea_relation_persister.pipeline.validate",
        side_effect=IdeaRelationValidationError("doc_id", "empty"),
    ):
        with pytest.raises(IdeaRelationValidationError):
            pipeline.run(make_valid_input())


def test_pipeline_propagates_extraction_failed() -> None:
    # ExtractionFailed は run() から伝播する（ルーターが 502 にマップする）
    pipeline = _make_pipeline()

    with (
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.validate",
            return_value=make_valid_input(),
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.structure_document",
            return_value=[],
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.extract_triplets",
            side_effect=ExtractionFailed("LLM error"),
        ),
    ):
        with pytest.raises(ExtractionFailed):
            pipeline.run(make_valid_input())


def test_pipeline_propagates_graph_store_unavailable() -> None:
    # GraphStoreUnavailable は run() から伝播する（ルーターが 503 にマップする）
    pipeline = _make_pipeline()

    with (
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.validate",
            return_value=make_valid_input(),
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.structure_document",
            return_value=[],
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.extract_triplets",
            return_value=[],
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.persist_to_graph",
            side_effect=GraphStoreUnavailable("unreachable"),
        ),
    ):
        with pytest.raises(GraphStoreUnavailable):
            pipeline.run(make_valid_input())


def test_pipeline_propagates_persist_failed() -> None:
    # PersistFailed は run() から伝播する（ルーターが 500 にマップする）
    pipeline = _make_pipeline()

    with (
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.validate",
            return_value=make_valid_input(),
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.structure_document",
            return_value=[],
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.extract_triplets",
            return_value=[],
        ),
        patch(
            "origin_spyglass.idea_relation_persister.pipeline.persist_to_graph",
            side_effect=PersistFailed("write error"),
        ),
    ):
        with pytest.raises(PersistFailed):
            pipeline.run(make_valid_input())

"""STEP3: スキーマ制約付き extractor 構築のテスト。

SchemaLLMPathExtractor の初期化引数と例外変換を検証する。
"""

from unittest.mock import MagicMock, patch

import pytest

from origin_spyglass.idea_relation_persister.extractor import (
    TripletSchemaConfig,
    build_kg_extractor,
)
from origin_spyglass.idea_relation_persister.types import ExtractionFailed

from ._helpers import make_valid_input


def _schema() -> TripletSchemaConfig:
    return TripletSchemaConfig(
        entities=["User", "Product", "Organization", "Event"],
        relations=["WORKS_FOR", "PARTICIPATED_IN", "PURCHASED", "LOCATED_IN"],
        validation_schema={
            "User": ["WORKS_FOR", "PARTICIPATED_IN", "PURCHASED"],
            "Organization": ["LOCATED_IN"],
            "Event": ["PARTICIPATED_IN"],
        },
    )


def test_build_kg_extractor_returns_schema_extractor() -> None:
    mock_llm = MagicMock()

    with (
        patch(
            "origin_spyglass.idea_relation_persister.extractor._load_triplet_schema",
            return_value=_schema(),
        ),
        patch(
            "origin_spyglass.idea_relation_persister.extractor.SchemaLLMPathExtractor"
        ) as MockExtractor,
    ):
        instance = MockExtractor.return_value
        result = build_kg_extractor(mock_llm, make_valid_input())

    assert result is instance


def test_build_kg_extractor_initializes_extractor_with_schema() -> None:
    # YAML 由来スキーマが SchemaLLMPathExtractor に渡ること
    mock_llm = MagicMock()

    with (
        patch(
            "origin_spyglass.idea_relation_persister.extractor._load_triplet_schema",
            return_value=_schema(),
        ),
        patch(
            "origin_spyglass.idea_relation_persister.extractor.SchemaLLMPathExtractor"
        ) as MockExtractor,
    ):
        build_kg_extractor(mock_llm, make_valid_input())

    call_kwargs = MockExtractor.call_args.kwargs
    assert call_kwargs["llm"] is mock_llm
    assert call_kwargs["possible_entities"] == _schema().entities
    assert call_kwargs["possible_relations"] == _schema().relations
    assert call_kwargs["kg_validation_schema"] == _schema().validation_schema
    assert call_kwargs["strict"] is True
    assert call_kwargs["num_workers"] == 1


def test_build_kg_extractor_prompt_contains_frontmatter_hints() -> None:
    # frontmatter 情報が抽出プロンプトに埋め込まれていること
    input_ = make_valid_input()

    with (
        patch(
            "origin_spyglass.idea_relation_persister.extractor._load_triplet_schema",
            return_value=_schema(),
        ),
        patch(
            "origin_spyglass.idea_relation_persister.extractor.SchemaLLMPathExtractor"
        ) as MockExtractor,
    ):
        build_kg_extractor(MagicMock(), input_)

    call_kwargs = MockExtractor.call_args.kwargs
    assert "tech" in call_kwargs["extract_prompt"]
    assert "Test Doc" in call_kwargs["extract_prompt"]


def test_build_kg_extractor_raises_extraction_failed_on_constructor_error() -> None:
    # コンストラクタ自体の失敗は ExtractionFailed に変換される

    with (
        patch(
            "origin_spyglass.idea_relation_persister.extractor._load_triplet_schema",
            return_value=_schema(),
        ),
        patch(
            "origin_spyglass.idea_relation_persister.extractor.SchemaLLMPathExtractor"
        ) as MockExtractor,
    ):
        MockExtractor.side_effect = RuntimeError("LLM unavailable")
        with pytest.raises(ExtractionFailed):
            build_kg_extractor(MagicMock(), make_valid_input())


def test_build_kg_extractor_propagates_schema_load_error() -> None:
    # 設定読込失敗も ExtractionFailed として扱う

    with patch(
        "origin_spyglass.idea_relation_persister.extractor._load_triplet_schema",
        side_effect=ExtractionFailed("schema invalid"),
    ):
        with pytest.raises(ExtractionFailed):
            build_kg_extractor(MagicMock(), make_valid_input())

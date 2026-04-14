"""STEP3: LLM トリプレット抽出のテスト

SimpleLLMPathExtractor は LLM を呼ぶため、patch で差し替えてテストする。
実装では extractor(nodes)（TransformComponent.__call__）を使うため、
モック時は instance.return_value / instance.side_effect で制御する点に注意。
"""

from unittest.mock import MagicMock, patch

import pytest

from origin_spyglass.idea_relation_persister.extractor import extract_triplets
from origin_spyglass.idea_relation_persister.types import ExtractionFailed

from ._helpers import make_valid_input

try:
    from llama_index.core.schema import TextNode  # type: ignore[import-untyped]
except Exception:
    # llama-index が環境にない場合は MagicMock で代替する
    TextNode = None  # type: ignore[assignment,misc]


def _make_nodes() -> list:  # type: ignore[type-arg]
    if TextNode is None:
        return [MagicMock()]
    return [TextNode(text="Alice knows Bob.", metadata={"doc_id": "doc-001"})]


def test_extract_triplets_returns_nodes() -> None:
    nodes = _make_nodes()
    mock_llm = MagicMock()

    with patch(
        "origin_spyglass.idea_relation_persister.extractor.SimpleLLMPathExtractor"
    ) as MockExtractor:
        instance = MockExtractor.return_value
        # extractor(nodes) は __call__ を呼ぶので return_value で戻り値を設定する
        instance.return_value = nodes
        result = extract_triplets(nodes, mock_llm, make_valid_input())

    assert result == nodes
    # __call__ が nodes を引数に一度呼ばれたことを確認
    instance.assert_called_once_with(nodes)


def test_extract_triplets_initializes_extractor_with_llm() -> None:
    # SimpleLLMPathExtractor のコンストラクタに llm と num_workers が正しく渡るか確認
    nodes = _make_nodes()
    mock_llm = MagicMock()

    with patch(
        "origin_spyglass.idea_relation_persister.extractor.SimpleLLMPathExtractor"
    ) as MockExtractor:
        instance = MockExtractor.return_value
        instance.extract.return_value = nodes
        extract_triplets(nodes, mock_llm, make_valid_input())

    call_kwargs = MockExtractor.call_args.kwargs
    assert call_kwargs["llm"] is mock_llm
    # num_workers=1 は FastAPI async context でのスレッド競合を防ぐため固定
    assert call_kwargs["num_workers"] == 1


def test_extract_triplets_prompt_contains_domain() -> None:
    # frontmatter.domain がプロンプトに埋め込まれていること
    nodes = _make_nodes()

    with patch(
        "origin_spyglass.idea_relation_persister.extractor.SimpleLLMPathExtractor"
    ) as MockExtractor:
        instance = MockExtractor.return_value
        instance.extract.return_value = nodes
        extract_triplets(nodes, MagicMock(), make_valid_input())

    call_kwargs = MockExtractor.call_args.kwargs
    assert "tech" in call_kwargs["extract_prompt"]


def test_extract_triplets_raises_extraction_failed_on_error() -> None:
    # コンストラクタ自体が失敗した場合も ExtractionFailed に変換される
    nodes = _make_nodes()

    with patch(
        "origin_spyglass.idea_relation_persister.extractor.SimpleLLMPathExtractor"
    ) as MockExtractor:
        MockExtractor.side_effect = RuntimeError("LLM unavailable")
        with pytest.raises(ExtractionFailed):
            extract_triplets(nodes, MagicMock(), make_valid_input())


def test_extract_triplets_raises_extraction_failed_on_extract_error() -> None:
    # extractor(nodes)（__call__）が失敗した場合も ExtractionFailed に変換される
    nodes = _make_nodes()

    with patch(
        "origin_spyglass.idea_relation_persister.extractor.SimpleLLMPathExtractor"
    ) as MockExtractor:
        instance = MockExtractor.return_value
        # extractor(nodes) → __call__ の side_effect を設定する
        instance.side_effect = ValueError("parse error")
        with pytest.raises(ExtractionFailed):
            extract_triplets(nodes, MagicMock(), make_valid_input())

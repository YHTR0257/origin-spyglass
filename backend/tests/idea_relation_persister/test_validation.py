"""STEP1: バリデーションのテスト

validate() は pure function（外部依存なし）なのでモックは不要。
fail-fast 方針の確認と境界値（chunk_overlap < chunk_size, XML prefix）を重点的に検証する。
"""

import pytest

from origin_spyglass.idea_relation_persister.types import (
    IdeaRelationValidationError,
)
from origin_spyglass.idea_relation_persister.validation import validate

from ._helpers import make_frontmatter, make_valid_input

# --- 正常系 ---


def test_validate_passes_valid_input() -> None:
    # 正常入力は同一オブジェクトをそのまま返す
    result = validate(make_valid_input())
    assert result.doc_id == "doc-001"


def test_validate_passes_overlap_zero() -> None:
    # chunk_overlap=0 は chunk_size 未満なので許容される
    result = validate(make_valid_input(chunk_size=128, chunk_overlap=0))
    assert result.chunk_overlap == 0


def test_validate_passes_overlap_one_less_than_chunk_size() -> None:
    # chunk_overlap = chunk_size - 1 は境界値として正常
    result = validate(make_valid_input(chunk_size=128, chunk_overlap=127))
    assert result.chunk_overlap == 127


# --- doc_id 異常系 ---


def test_validate_rejects_empty_doc_id() -> None:
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(doc_id=""))
    assert exc.value.field == "doc_id"


def test_validate_rejects_whitespace_only_doc_id() -> None:
    # 空白のみは空文字と同じく無効
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(doc_id="   "))
    assert exc.value.field == "doc_id"


# --- body_text 異常系 ---


def test_validate_rejects_empty_body_text() -> None:
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(body_text=""))
    assert exc.value.field == "body_text"


def test_validate_rejects_whitespace_only_body_text() -> None:
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(body_text="   \n  "))
    assert exc.value.field == "body_text"


def test_validate_rejects_xml_prefix() -> None:
    # XML prefix は将来的にも対応しない（設計ポリシー）
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(body_text="<?xml version='1.0'?><root/>"))
    assert exc.value.field == "body_text"


def test_validate_rejects_xml_prefix_with_leading_whitespace() -> None:
    # BOM や先頭改行があっても lstrip() で検出できること
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(body_text="\n<?xml version='1.0'?>"))
    assert exc.value.field == "body_text"


# --- frontmatter 異常系 ---


def test_validate_rejects_empty_domain() -> None:
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(frontmatter=make_frontmatter(domain="")))
    assert exc.value.field == "frontmatter.domain"


def test_validate_rejects_empty_source_file() -> None:
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(frontmatter=make_frontmatter(source_file="")))
    assert exc.value.field == "frontmatter.source_file"


# --- chunk_overlap クロスフィールド制約 ---


def test_validate_rejects_overlap_equal_to_chunk_size() -> None:
    # chunk_overlap == chunk_size は境界値として無効（< が必要）
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(chunk_size=128, chunk_overlap=128))
    assert exc.value.field == "chunk_overlap"


def test_validate_rejects_overlap_greater_than_chunk_size() -> None:
    with pytest.raises(IdeaRelationValidationError) as exc:
        validate(make_valid_input(chunk_size=64, chunk_overlap=100))
    assert exc.value.field == "chunk_overlap"

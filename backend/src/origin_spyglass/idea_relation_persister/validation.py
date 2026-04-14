"""STEP1: 入力バリデーション"""

from datetime import date

from origin_spyglass.schemas.doc_relation import SourceType

from .types import (
    IdeaRelationPersisterInput,
    IdeaRelationValidationError,
    ValidatedIdeaRelationInput,
)


def validate(input: IdeaRelationPersisterInput) -> ValidatedIdeaRelationInput:
    """STEP1: 全フィールドを検証し、同一オブジェクトを返す。

    最初の違反で即座に失敗する（fail-fast）。

    Raises:
        IdeaRelationValidationError: バリデーション失敗時
    """
    if not input.doc_id.strip():
        raise IdeaRelationValidationError("doc_id", "must not be empty or whitespace-only")

    if not input.body_text.strip():
        raise IdeaRelationValidationError("body_text", "must not be empty or whitespace-only")

    if not input.frontmatter.domain.strip():
        raise IdeaRelationValidationError("frontmatter.domain", "must not be empty")

    if not input.frontmatter.source_file.strip():
        raise IdeaRelationValidationError("frontmatter.source_file", "must not be empty")

    if not isinstance(input.frontmatter.source_type, SourceType):
        raise IdeaRelationValidationError("frontmatter.source_type", "must be a valid SourceType")

    if not (0.0 <= input.frontmatter.confidence <= 1.0):
        raise IdeaRelationValidationError("frontmatter.confidence", "must be in [0.0, 1.0]")

    if not isinstance(input.frontmatter.date, date):
        raise IdeaRelationValidationError("frontmatter.date", "must be a date")

    if input.chunk_overlap >= input.chunk_size:
        raise IdeaRelationValidationError(
            "chunk_overlap",
            f"must be less than chunk_size ({input.chunk_size}), got {input.chunk_overlap}",
        )

    stripped = input.body_text.lstrip()
    if stripped.startswith("<?xml") or stripped.startswith("<xml"):
        raise IdeaRelationValidationError("body_text", "must not contain XML prefix")

    return input

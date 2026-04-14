"""idea_relation_persister テスト用の共有ファクトリ関数。

各テストファイルで重複していた入力データ生成ロジックをまとめる。
"""

from datetime import date

from origin_spyglass.idea_relation_persister.types import (
    IdeaFrontmatterMeta,
    IdeaRelationPersisterInput,
    IdeaRelationPersisterOutput,
)
from origin_spyglass.schemas.doc_relation import SourceType

_DEFAULT_FRONTMATTER = dict(
    domain="tech",
    tags=["ai"],
    title="Test Doc",
    created_at="2026-04-14T00:00:00",
    source_file="test.md",
    source_type=SourceType.LOCAL_MARKDOWN,
    confidence=0.9,
    date=date(2026, 4, 1),
)


def make_frontmatter(**overrides: object) -> IdeaFrontmatterMeta:
    """デフォルト値から IdeaFrontmatterMeta を生成する。"""
    return IdeaFrontmatterMeta(**{**_DEFAULT_FRONTMATTER, **overrides})  # type: ignore[arg-type]


def make_valid_input(**overrides: object) -> IdeaRelationPersisterInput:
    """全フィールドが正常なデフォルト値で IdeaRelationPersisterInput を生成する。

    個別フィールドを上書きしたい場合は **overrides に渡す。
    frontmatter を丸ごと差し替える場合は frontmatter=make_frontmatter(...) を渡す。
    """
    frontmatter = overrides.pop("frontmatter", make_frontmatter())
    defaults: dict[str, object] = {
        "doc_id": "doc-001",
        "frontmatter": frontmatter,
        "body_text": "Alice knows Bob.",
        "chunk_size": 256,
        "chunk_overlap": 32,
    }
    defaults.update(overrides)
    return IdeaRelationPersisterInput(**defaults)  # type: ignore[arg-type]


def make_valid_output(**overrides: object) -> IdeaRelationPersisterOutput:
    """正常系の IdeaRelationPersisterOutput を生成する。"""
    defaults: dict[str, object] = {
        "doc_id": "doc-001",
        "persisted": True,
        "node_count": 3,
        "edge_count": 2,
        "elapsed_ms": 50,
        "warnings": [],
    }
    defaults.update(overrides)
    return IdeaRelationPersisterOutput(**defaults)  # type: ignore[arg-type]

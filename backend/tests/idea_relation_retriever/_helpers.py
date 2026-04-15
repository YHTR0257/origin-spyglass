"""テスト共通ファクトリ関数"""

from origin_spyglass.idea_relation_retriever.types import (
    IdeaRelationRetrieverInput,
    IdeaRelationRetrieverOutput,
    RelatedIdea,
)


def make_valid_input(**overrides: object) -> IdeaRelationRetrieverInput:
    defaults: dict[str, object] = {
        "question": "量子コンピュータと古典コンピュータの関係は？",
        "max_results": 10,
        "domain": None,
        "user_id": None,
    }
    defaults.update(overrides)
    return IdeaRelationRetrieverInput(**defaults)  # type: ignore[arg-type]


def make_related_idea(**overrides: object) -> RelatedIdea:
    defaults: dict[str, object] = {
        "node_id": "node-001",
        "title": "量子コンピュータ",
        "body_snippet": "量子コンピュータは量子力学の原理を...",
        "relevance_score": 0.92,
    }
    defaults.update(overrides)
    return RelatedIdea(**defaults)  # type: ignore[arg-type]


def make_valid_output(**overrides: object) -> IdeaRelationRetrieverOutput:
    defaults: dict[str, object] = {
        "question": "量子コンピュータと古典コンピュータの関係は？",
        "answer": "量子コンピュータは古典コンピュータとは異なる計算原理を持ち...",
        "related_ideas": [make_related_idea()],
        "elapsed_ms": 120,
        "warnings": [],
    }
    defaults.update(overrides)
    return IdeaRelationRetrieverOutput(**defaults)  # type: ignore[arg-type]

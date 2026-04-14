"""STEP3: スキーマ制約付き Extractor 構築"""

from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import yaml
from llama_index.core.indices.property_graph import (  # type: ignore[import-untyped]
    SchemaLLMPathExtractor,
)
from llama_index.core.llms import LLM  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from yaml import YAMLError

from spyglass_utils.logging import get_logger
from spyglass_utils.settings import get_settings

from .types import ExtractionFailed, IdeaFrontmatterMeta, ValidatedIdeaRelationInput

_logger = get_logger(__name__)

# frontmatter ヒントを埋め込んだ日本語抽出プロンプト。
# {text} と {max_triplets_per_chunk} は SchemaLLMPathExtractor が実行時に展開する。
_PROMPT_TEMPLATE = """\
次のテキストから、知識グラフ用のトリプレットを抽出してください。
スキーマ外の型・関係は出力せず、事実関係のみを抽出してください。

ドキュメントのコンテキスト:
- ドメイン: {domain}
- タイトル: {title}
- タグ: {tags}

最大抽出件数: {max_triplets_per_chunk}

テキスト:
{text}
"""


class TripletSchemaConfig(BaseModel):
    """YAML から読み込むトリプレット許可スキーマ。"""

    model_config = ConfigDict(extra="forbid")

    entities: list[str] = Field(min_length=1)
    relations: list[str] = Field(min_length=1)
    validation_schema: dict[str, list[str]]

    @model_validator(mode="after")
    def _validate_consistency(self) -> "TripletSchemaConfig":
        entity_set = set(self.entities)
        relation_set = set(self.relations)

        unknown_entities = sorted(set(self.validation_schema) - entity_set)
        if unknown_entities:
            joined = ", ".join(unknown_entities)
            raise ValueError(f"validation_schema has unknown entities: {joined}")

        unknown_relations = sorted(
            {
                relation
                for allowed_relations in self.validation_schema.values()
                for relation in allowed_relations
                if relation not in relation_set
            }
        )
        if unknown_relations:
            joined = ", ".join(unknown_relations)
            raise ValueError(f"validation_schema has unknown relations: {joined}")

        return self


def _build_prompt(frontmatter: IdeaFrontmatterMeta) -> str:
    """frontmatter のヒントをプロンプトテンプレートにリテラル置換する。"""
    return (
        _PROMPT_TEMPLATE.replace("{domain}", frontmatter.domain)
        .replace("{title}", frontmatter.title or "")
        .replace("{tags}", ", ".join(frontmatter.tags))
    )


def _resolve_schema_path() -> Path:
    configured_path = Path(get_settings().triplet_schema_path)
    if configured_path.is_absolute():
        return configured_path

    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / configured_path


@lru_cache(maxsize=1)
def _load_triplet_schema() -> TripletSchemaConfig:
    path = _resolve_schema_path()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ExtractionFailed(f"triplet schema file is not readable: {path}") from exc
    except YAMLError as exc:
        raise ExtractionFailed(f"triplet schema yaml is invalid: {path}") from exc

    if not isinstance(raw, dict):
        raise ExtractionFailed("triplet schema yaml must be a mapping")

    try:
        return TripletSchemaConfig.model_validate(raw)
    except ValidationError as exc:
        raise ExtractionFailed(f"triplet schema validation failed: {exc}") from exc


def build_kg_extractor(
    llm: LLM,
    input: ValidatedIdeaRelationInput,
) -> SchemaLLMPathExtractor:
    """STEP3: スキーマ制約付きの KG extractor を構築する。

    YAML 定義された entities / relations / validation_schema を使って
    SchemaLLMPathExtractor を生成する。strict は常時 True で固定する。

    Args:
        llm: LlamaIndex LLM インスタンス
        input: バリデーション済み入力（frontmatter ヒント参照用）

    Returns:
        PropertyGraphIndex.from_documents に渡す SchemaLLMPathExtractor

    Raises:
        ExtractionFailed: 設定読込や extractor 構築に失敗した場合
    """
    try:
        schema = _load_triplet_schema()
        return SchemaLLMPathExtractor(
            llm=llm,
            # SchemaLLMPathExtractor の型注釈は実装より厳しく、
            # list[str] / dict[str, list[str]] を受け取れる実装と不整合があるため cast する。
            possible_entities=cast(Any, schema.entities),
            possible_relations=cast(Any, schema.relations),
            kg_validation_schema=cast(Any, schema.validation_schema),
            strict=True,
            max_triplets_per_chunk=10,
            num_workers=1,
            extract_prompt=_build_prompt(input.frontmatter),
        )
    except ExtractionFailed:
        raise
    except Exception as exc:
        _logger.error("KG extractor build failed: %s", exc)
        raise ExtractionFailed(f"KG extractor build failed: {exc}") from exc

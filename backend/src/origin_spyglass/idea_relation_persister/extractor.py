"""STEP3: LLM トリプレット抽出"""

from llama_index.core.indices.property_graph import (
    SimpleLLMPathExtractor,  # type: ignore[import-untyped]
)
from llama_index.core.llms import LLM  # type: ignore[import-untyped]
from llama_index.core.schema import TextNode  # type: ignore[import-untyped]

from spyglass_utils.logging import get_logger

from .types import ExtractionFailed, IdeaFrontmatterMeta, ValidatedIdeaRelationInput

_logger = get_logger(__name__)

# frontmatter ヒントを埋め込んだ日本語抽出プロンプトのテンプレート。
# {text} は SimpleLLMPathExtractor が実行時に各ノードのテキストに置き換える。
_PROMPT_TEMPLATE = """\
以下のテキストから、知識グラフ用の (主語, 述語, 目的語) トリプレットを抽出してください。
意味のある事実関係のみを対象とし、Markdown の記号は含めないでください。

ドキュメントのコンテキスト:
- ドメイン: {domain}
- タイトル: {title}
- タグ: {tags}

テキスト:
{text}

抽出結果は JSON 配列で返してください。
各要素は {{"subject": "...", "predicate": "...", "object": "..."}} の形式にしてください。
"""


def _build_prompt(frontmatter: IdeaFrontmatterMeta) -> str:
    """frontmatter のヒントをプロンプトテンプレートにリテラル置換する。"""
    return (
        _PROMPT_TEMPLATE.replace("{domain}", frontmatter.domain)
        .replace("{title}", frontmatter.title or "")
        .replace("{tags}", ", ".join(frontmatter.tags))
    )


def extract_triplets(
    nodes: list[TextNode],
    llm: LLM,
    input: ValidatedIdeaRelationInput,
) -> list[TextNode]:
    """STEP3: 各ノードから (subject, predicate, object) トリプレットを抽出する。

    SimpleLLMPathExtractor を使用して LLM にトリプレット抽出を依頼する。
    frontmatter の domain / title / tags を抽出ヒントとしてプロンプトに注入する。

    Args:
        nodes: STEP2 で構造化された TextNode リスト
        llm: LlamaIndex LLM インスタンス
        input: バリデーション済み入力（frontmatter ヒント参照用）

    Returns:
        トリプレット情報が付与された TextNode リスト

    Raises:
        ExtractionFailed: LLM 呼び出しまたはパースが失敗した場合
    """
    try:
        extractor = SimpleLLMPathExtractor(
            llm=llm,
            max_paths_per_chunk=10,
            num_workers=1,
            extract_prompt=_build_prompt(input.frontmatter),
        )
        # __call__ は TransformComponent の公開 sync API
        enriched: list[TextNode] = extractor(nodes)  # type: ignore[attr-defined,assignment]
        return enriched
    except Exception as exc:
        _logger.error("Triplet extraction failed: %s", exc)
        raise ExtractionFailed(f"LLM triplet extraction failed: {exc}") from exc

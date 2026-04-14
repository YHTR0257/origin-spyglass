"""STEP2: 2段階ドキュメント構造化"""

from llama_index.core import Document  # type: ignore[import-untyped]
from llama_index.core.node_parser import (  # type: ignore[import-untyped]
    MarkdownNodeParser,
    SentenceSplitter,
)
from llama_index.core.schema import TextNode  # type: ignore[import-untyped]

from .types import ValidatedIdeaRelationInput


def structure_document(input: ValidatedIdeaRelationInput) -> list[TextNode]:
    """STEP2: 2段階ドキュメント構造化。

    Phase 1: MarkdownNodeParser で見出し単位に分割し、heading breadcrumb を各ノードに注入する。
    Phase 2: SentenceSplitter で chunk_size / chunk_overlap に基づき再分割する。

    Returns:
        TextNode のフラットリスト（STEP3 のトリプレット抽出に渡す）
    """
    doc = Document(
        text=input.body_text,
        metadata={
            "doc_id": input.doc_id,
            "domain": input.frontmatter.domain,
            "title": input.frontmatter.title or "",
            "tags": ",".join(input.frontmatter.tags),
            "source_file": input.frontmatter.source_file,
            "source_type": str(input.frontmatter.source_type),
            "confidence": str(input.frontmatter.confidence),
            "date": str(input.frontmatter.date),
        },
        excluded_llm_metadata_keys=["confidence", "date"],
        excluded_embed_metadata_keys=["confidence", "date", "source_type"],
    )

    # Phase 1: 見出し単位に分割（heading breadcrumb を metadata に注入）
    md_parser = MarkdownNodeParser(include_metadata=True)
    heading_nodes = md_parser.get_nodes_from_documents([doc])

    # Phase 2: 各見出しセクションをコンテキスト長で再分割
    splitter = SentenceSplitter(
        chunk_size=input.chunk_size,
        chunk_overlap=input.chunk_overlap,
    )
    final_nodes: list[TextNode] = []
    for node in heading_nodes:
        sub_nodes = splitter.get_nodes_from_documents(
            [
                Document(
                    text=node.get_content(),
                    metadata=node.metadata,
                )
            ]
        )
        final_nodes.extend(sub_nodes)  # type: ignore[arg-type]

    return final_nodes

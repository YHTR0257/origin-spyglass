"""STEP2: ドキュメント構造化のテスト

structure_document() は MarkdownNodeParser / SentenceSplitter（llama-index の純粋処理）を使うため
LLM や外部 I/O に依存せず、モックなしで実行できる。
"""

from origin_spyglass.idea_relation_persister.structure import structure_document
from origin_spyglass.idea_relation_persister.types import IdeaRelationPersisterInput

from ._helpers import make_frontmatter, make_valid_input


def test_structure_returns_at_least_one_node() -> None:
    nodes = structure_document(make_valid_input())
    assert len(nodes) > 0


def test_structure_nodes_have_doc_id_in_metadata() -> None:
    # STEP4 で逆引き用の doc_id をノードに付与するため、構造化時点で metadata に含める
    nodes = structure_document(make_valid_input())
    for node in nodes:
        assert node.metadata.get("doc_id") == "doc-001"


def test_structure_nodes_have_domain_in_metadata() -> None:
    # frontmatter の domain が各ノードに伝播していること（STEP3 のヒント参照用）
    nodes = structure_document(make_valid_input())
    for node in nodes:
        assert node.metadata.get("domain") == "tech"


def test_structure_nodes_contain_body_text() -> None:
    # 元の本文テキストが分割後のノード群に保持されていること
    nodes = structure_document(make_valid_input(body_text="The quick brown fox."))
    combined = " ".join(n.get_content() for n in nodes)
    assert "quick brown fox" in combined


def test_structure_heading_split_produces_multiple_nodes() -> None:
    # Phase 1: MarkdownNodeParser が見出し境界で分割することを確認
    body = "# Section One\n\nContent one.\n\n## Sub Section\n\nContent two.\n"
    nodes = structure_document(make_valid_input(body_text=body))
    assert len(nodes) >= 2


def test_structure_respects_chunk_size() -> None:
    # Phase 2: chunk_size が小さい場合に SentenceSplitter が再分割することを確認
    input_ = IdeaRelationPersisterInput(
        doc_id="doc-002",
        frontmatter=make_frontmatter(title="Long Doc", source_file="long.md", confidence=0.8),
        body_text="word " * 1000,
        chunk_size=64,
        chunk_overlap=8,
    )
    nodes = structure_document(input_)
    assert len(nodes) > 1

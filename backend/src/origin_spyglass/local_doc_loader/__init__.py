"""Local Doc Loader public API.

このモジュールは単一ドキュメント入力を前提にする。
複数ドキュメントの処理は呼び出し側でループする。
"""

from datetime import UTC, datetime

from .cleaner import MarkdownCleaner
from .converter import DocumentConverter, FrontmatterConverter
from .types import FrontmatterMeta, LocalDocumentInput, LocalDocumentOutput


def load_document(document: LocalDocumentInput, llm=None) -> LocalDocumentOutput:
    """単一ドキュメントを Markdown + Frontmatter へ変換する。"""
    converter = DocumentConverter()
    frontmatter_converter = FrontmatterConverter()
    cleaner = MarkdownCleaner()

    mime = converter.detect_format(document.file_bytes, document.filename)
    markdown = converter.convert_to_markdown(document.file_bytes, mime, document.filename)

    fallback_meta = FrontmatterMeta(
        domain=document.domain,
        tags=document.tags,
        title=document.title,
        created_at=datetime.now(UTC).isoformat(),
        source_file=document.filename,
    )

    with_frontmatter = frontmatter_converter.add_frontmatter(markdown, fallback_meta)
    cleaned_markdown = cleaner.clean(with_frontmatter, llm=llm, filename=document.filename)

    parsed_meta, _ = frontmatter_converter.parse_frontmatter(
        cleaned_markdown,
        filename=document.filename,
    )

    return LocalDocumentOutput(
        mime=mime,
        markdown=cleaned_markdown,
        meta=parsed_meta or fallback_meta,
    )


__all__ = [
    "DocumentConverter",
    "FrontmatterConverter",
    "MarkdownCleaner",
    "FrontmatterMeta",
    "LocalDocumentInput",
    "LocalDocumentOutput",
    "load_document",
]

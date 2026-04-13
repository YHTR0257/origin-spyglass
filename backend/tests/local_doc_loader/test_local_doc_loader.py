import socket

import pytest

from origin_spyglass.local_doc_loader import load_document
from origin_spyglass.local_doc_loader.cleaner import MarkdownCleaner
from origin_spyglass.local_doc_loader.converter import DocumentConverter, FrontmatterConverter
from origin_spyglass.local_doc_loader.types import (
    DocumentConversionError,
    LocalDocumentInput,
    MarkdownCleaningError,
    TextDecodingError,
    UnsupportedMimeTypeError,
)


class _DummyResult:
    def __init__(self, text_content: str) -> None:
        self.text_content = text_content


class _DummyMarkItDown:
    def convert(self, _path: str) -> _DummyResult:
        return _DummyResult("converted markdown")


class _ErrorMarkItDown:
    def convert(self, _path: str) -> _DummyResult:
        raise RuntimeError("broken markitdown")


class _BrokenLlm:
    def complete(self, _prompt: str):
        raise RuntimeError("llm failed")


def test_detect_format_rejects_unsupported_mime(monkeypatch: pytest.MonkeyPatch) -> None:
    converter = DocumentConverter()
    logged: dict[str, str] = {}

    def _capture_error(message: str, *args, **_kwargs) -> None:
        logged["message"] = message % args

    monkeypatch.setattr(
        "origin_spyglass.local_doc_loader.converter.magic.from_buffer",
        lambda *_args, **_kwargs: "application/msword",
    )
    monkeypatch.setattr(
        "origin_spyglass.local_doc_loader.converter.logger.error",
        _capture_error,
    )

    with pytest.raises(UnsupportedMimeTypeError) as exc:
        converter.detect_format(b"dummy", "sample.docx")

    assert exc.value.filename == "sample.docx"
    assert exc.value.mime == "application/msword"
    assert "sample.docx" in logged["message"]
    assert "application/msword" in logged["message"]


def test_detect_format_accepts_supported_mime(monkeypatch: pytest.MonkeyPatch) -> None:
    converter = DocumentConverter()
    monkeypatch.setattr(
        "origin_spyglass.local_doc_loader.converter.magic.from_buffer",
        lambda *_args, **_kwargs: "text/html",
    )

    assert converter.detect_format(b"<h1>hello</h1>", "index.html") == "text/html"


def test_convert_markdown_utf8() -> None:
    converter = DocumentConverter()

    markdown = converter.convert_to_markdown(b"# hello", "text/markdown", "a.md")

    assert markdown == "# hello"


def test_convert_empty_markdown() -> None:
    converter = DocumentConverter()

    markdown = converter.convert_to_markdown(b"", "text/plain", "empty.md")

    assert markdown == ""


def test_convert_invalid_utf8_raises_typed_error() -> None:
    converter = DocumentConverter()

    with pytest.raises(TextDecodingError):
        converter.convert_to_markdown(b"\xff\xfe", "text/plain", "broken.md")


def test_convert_json_to_code_block() -> None:
    converter = DocumentConverter()

    markdown = converter.convert_to_markdown(
        b'{"title": "spec", "count": 2}',
        "application/json",
        "sample.json",
    )

    assert markdown.startswith("```json")
    assert '"title": "spec"' in markdown
    assert markdown.endswith("```")


def test_convert_invalid_json_raises_typed_error() -> None:
    converter = DocumentConverter()

    with pytest.raises(DocumentConversionError):
        converter.convert_to_markdown(b'{"title":}', "application/json", "broken.json")


def test_convert_pdf_uses_markitdown(monkeypatch: pytest.MonkeyPatch) -> None:
    converter = DocumentConverter()
    monkeypatch.setattr("origin_spyglass.local_doc_loader.converter.MarkItDown", _DummyMarkItDown)

    markdown = converter.convert_to_markdown(b"%PDF-1.4", "application/pdf", "sample.pdf")

    assert markdown == "converted markdown"


def test_convert_pdf_markitdown_error(monkeypatch: pytest.MonkeyPatch) -> None:
    converter = DocumentConverter()
    monkeypatch.setattr("origin_spyglass.local_doc_loader.converter.MarkItDown", _ErrorMarkItDown)

    with pytest.raises(DocumentConversionError):
        converter.convert_to_markdown(b"%PDF-1.4", "application/pdf", "sample.pdf")


def test_frontmatter_add_is_idempotent() -> None:
    frontmatter_converter = FrontmatterConverter()
    original = "---\ncreated_at: 2026-01-01T00:00:00+00:00\nsource_file: a.md\n---\n\nBody"

    result = frontmatter_converter.add_frontmatter(
        original,
        frontmatter_converter.parse_frontmatter(original)[0],
    )

    assert result == original


def test_frontmatter_invalid_yaml_fallback() -> None:
    frontmatter_converter = FrontmatterConverter()
    broken = "---\ntags: [abc\n---\n\nBody"

    meta, body = frontmatter_converter.parse_frontmatter(broken, filename="broken.md")

    assert meta is None
    assert body == broken


def test_frontmatter_valid_yaml_parse() -> None:
    frontmatter_converter = FrontmatterConverter()
    markdown = (
        "---\n"
        "domain: ai\n"
        "tags:\n"
        "  - llm\n"
        "created_at: 2026-04-14T00:00:00+00:00\n"
        "source_file: sample.md\n"
        "---\n\n"
        "Body"
    )

    meta, body = frontmatter_converter.parse_frontmatter(markdown, filename="sample.md")

    assert meta is not None
    assert meta.domain == "ai"
    assert meta.tags == ["llm"]
    assert meta.title == "sample"
    assert body == "Body"


def test_cleaner_rule_based_cleans_text() -> None:
    cleaner = MarkdownCleaner()
    raw = "Hello-\nWorld\n2\n\n\nNext line"

    cleaned = cleaner.clean(raw, filename="sample.md")

    assert "HelloWorld" in cleaned
    assert "\n\n\n" not in cleaned
    assert "\n2\n" not in cleaned


def test_cleaner_wraps_llm_failure() -> None:
    cleaner = MarkdownCleaner()

    with pytest.raises(MarkdownCleaningError):
        cleaner.clean("text", llm=_BrokenLlm(), filename="sample.md")


def test_load_document_single_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "origin_spyglass.local_doc_loader.converter.magic.from_buffer",
        lambda *_args, **_kwargs: "text/plain",
    )

    output = load_document(
        LocalDocumentInput(
            filename="note.md",
            file_bytes=b"hello",
            domain="research",
            tags=["draft"],
        )
    )

    assert output.mime == "text/plain"
    assert output.meta.source_file == "note.md"
    assert output.meta.domain == "research"
    assert output.meta.tags == ["draft"]
    assert output.markdown.startswith("---\n")


def test_markdown_conversion_has_no_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    converter = DocumentConverter()
    state = {"called": False}

    def _forbidden_connection(*_args, **_kwargs):
        state["called"] = True
        raise AssertionError("network access should not be used")

    monkeypatch.setattr(socket, "create_connection", _forbidden_connection)

    markdown = converter.convert_to_markdown(b"# title", "text/plain", "a.md")

    assert markdown == "# title"
    assert state["called"] is False

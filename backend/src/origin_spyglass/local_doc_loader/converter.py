"""ドキュメント変換・Frontmatter 付与・パースロジック"""

import json
import re
import tempfile
from typing import Any

import magic
import yaml
from markitdown import MarkItDown
from pydantic import ValidationError
from yaml import YAMLError

from spyglass_utils.logging import get_logger

from .types import (
    DocumentConversionError,
    FrontmatterMeta,
    FrontmatterParseError,
    TextDecodingError,
    UnsupportedMimeTypeError,
)

logger = get_logger(__name__)

# サポートする MIME タイプと対応する拡張子
SUPPORTED_MIME: dict[str, str] = {
    "application/json": ".json",
    "application/pdf": ".pdf",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/plain": ".md",
}


class DocumentConverter:
    """ドキュメントの MIME 判定と Markdown 変換を担うクラス

    サポートフォーマット: JSON / PDF / Markdown / HTML
    """

    def detect_format(self, file_bytes: bytes, filename: str) -> str:
        """MIME タイプ + 拡張子でフォーマットを判定する

        Args:
            file_bytes: ファイルの内容
            filename: 元のファイル名（ログ用）

        Returns:
            検出された MIME タイプ文字列

        Raises:
            ValueError: サポート外のフォーマットの場合
        """
        mime = magic.from_buffer(file_bytes, mime=True)
        if mime not in SUPPORTED_MIME:
            detail = f"Supported: {list(SUPPORTED_MIME.keys())}"
            logger.error(
                "Unsupported MIME type detected: filename=%s mime=%s detail=%s",
                filename,
                mime,
                detail,
            )
            raise UnsupportedMimeTypeError(
                filename=filename,
                mime=mime,
                detail=detail,
            )
        return mime

    def _decode_utf8(self, file_bytes: bytes, *, filename: str, mime: str) -> str:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            logger.error(
                "UTF-8 decode failed: filename=%s mime=%s detail=%s",
                filename,
                mime,
                str(e),
                exc_info=True,
            )
            raise TextDecodingError(filename=filename, mime=mime, detail=str(e)) from e

    def convert_to_markdown(self, file_bytes: bytes, mime: str, filename: str) -> str:
        """markitdown を使用してファイルを Markdown に変換する

        Args:
            file_bytes: ファイルの内容
            mime: detect_format() で取得した MIME タイプ

        Returns:
            変換後の Markdown テキスト

        Raises:
            RuntimeError: 変換に失敗した場合
        """
        if mime not in SUPPORTED_MIME:
            detail = "MIME is not in supported whitelist"
            logger.error(
                "Conversion requested with unsupported MIME: filename=%s mime=%s",
                filename,
                mime,
            )
            raise UnsupportedMimeTypeError(filename=filename, mime=mime, detail=detail)

        if mime in {"text/markdown", "text/plain"}:
            return self._decode_utf8(file_bytes, filename=filename, mime=mime)

        if mime == "application/json":
            decoded = self._decode_utf8(file_bytes, filename=filename, mime=mime)
            try:
                parsed = json.loads(decoded)
            except json.JSONDecodeError as e:
                logger.error(
                    "JSON parse failed: filename=%s mime=%s detail=%s",
                    filename,
                    mime,
                    str(e),
                    exc_info=True,
                )
                raise DocumentConversionError(filename=filename, mime=mime, detail=str(e)) from e
            pretty_json = json.dumps(parsed, ensure_ascii=False, indent=2)
            return f"```json\n{pretty_json}\n```"

        ext = SUPPORTED_MIME[mime]
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=True) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                result = MarkItDown().convert(tmp.name)
            return result.text_content or ""
        except Exception as e:
            logger.error(
                "Document conversion failed: filename=%s mime=%s detail=%s",
                filename,
                mime,
                str(e),
                exc_info=True,
            )
            raise DocumentConversionError(filename=filename, mime=mime, detail=str(e)) from e


_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


class FrontmatterConverter:
    """Markdown Frontmatter の付与・パースを担うクラス

    付与は冪等: 既存 Frontmatter がある場合はスキップする。
    """

    def is_frontmatter_present(self, markdown: str) -> bool:
        """Markdown の先頭に Frontmatter ブロックがあるか判定する"""
        return bool(_FRONTMATTER_RE.match(markdown))

    def parse_frontmatter(
        self,
        markdown: str,
        *,
        filename: str = "unknown",
    ) -> tuple[FrontmatterMeta | None, str]:
        """Frontmatter をパースして (meta, 本文) を返す

        Args:
            markdown: Frontmatter を含む可能性がある Markdown テキスト

        Returns:
            Frontmatter がある場合は (FrontmatterMeta, 本文テキスト)、
            ない場合は (None, 元のテキスト)
        """
        match = _FRONTMATTER_RE.match(markdown)
        if not match:
            return None, markdown

        yaml_block, body = match.group(1), match.group(2)
        try:
            data = yaml.safe_load(yaml_block) or {}
            if not isinstance(data, dict):
                raise FrontmatterParseError(
                    filename=filename,
                    detail="Frontmatter YAML must be a mapping",
                )
            _raw_tags = data.get("tags")
            tags: list[Any] = _raw_tags if isinstance(_raw_tags, list) else []
            meta = FrontmatterMeta(
                domain=str(data.get("domain", "general")),
                tags=[str(tag) for tag in tags],
                title=data.get("title"),
                created_at=str(data.get("created_at", "")),
                source_file=str(data.get("source_file", "")),
            )
            return meta, body.lstrip("\n")
        except (YAMLError, ValidationError, FrontmatterParseError) as e:
            logger.error(
                "Frontmatter parse failed, fallback to original markdown: filename=%s detail=%s",
                filename,
                str(e),
                exc_info=True,
            )
            return None, markdown

    def add_frontmatter(self, markdown: str, meta: FrontmatterMeta) -> str:
        """Frontmatter を Markdown の先頭に付与する

        冪等: 既存 Frontmatter がある場合はそのまま返す。

        Args:
            markdown: 対象の Markdown テキスト
            meta: 付与するメタデータ

        Returns:
            Frontmatter 付き Markdown テキスト
        """
        if self.is_frontmatter_present(markdown):
            return markdown
        frontmatter = yaml.dump(meta.model_dump(), allow_unicode=True, sort_keys=False)
        return f"---\n{frontmatter}---\n\n{markdown}"

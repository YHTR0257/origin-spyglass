"""ドキュメント変換・Frontmatter 付与・パースロジック"""

import re
import tempfile

import magic
import yaml
from markitdown import MarkItDown

from .types import FrontmatterMeta

# サポートする MIME タイプと対応する拡張子
SUPPORTED_MIME: dict[str, str] = {
    "application/json": ".json",
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


class DocumentConverter:
    """ドキュメントの MIME 判定と Markdown 変換を担うクラス

    サポートフォーマット: JSON / PDF / JPEG / PNG
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
            raise ValueError(
                f"Unsupported format: {mime} (file: {filename}). "
                f"Supported: {list(SUPPORTED_MIME.keys())}"
            )
        return mime

    def convert_to_markdown(self, file_bytes: bytes, mime: str) -> str:
        """markitdown を使用してファイルを Markdown に変換する

        Args:
            file_bytes: ファイルの内容
            mime: detect_format() で取得した MIME タイプ

        Returns:
            変換後の Markdown テキスト

        Raises:
            RuntimeError: 変換に失敗した場合
        """
        ext = SUPPORTED_MIME[mime]
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=True) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                result = MarkItDown().convert(tmp.name)
            return result.text_content or ""
        except Exception as e:
            raise RuntimeError(f"Conversion failed ({mime}): {e}") from e


_FRONTMATTER_RE = re.compile(r"^\s*---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


class FrontmatterConverter:
    """Markdown Frontmatter の付与・パースを担うクラス

    付与は冪等: 既存 Frontmatter がある場合はスキップする。
    """

    def is_frontmatter_present(self, markdown: str) -> bool:
        """Markdown の先頭に Frontmatter ブロックがあるか判定する"""
        return bool(_FRONTMATTER_RE.match(markdown))

    def parse_frontmatter(self, markdown: str) -> tuple[FrontmatterMeta | None, str]:
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
        data = yaml.safe_load(yaml_block) or {}
        meta = FrontmatterMeta(
            domain=data.get("domain", "general"),
            tags=data.get("tags") or [],
            title=data.get("title"),
            created_at=data.get("created_at", ""),
            source_file=data.get("source_file", ""),
        )
        return meta, body.lstrip("\n")

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

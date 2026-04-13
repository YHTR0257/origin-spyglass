"""Local Doc Loader の型定義。

単一ドキュメント入力の I/O スキーマと、呼び出し側が分岐可能な
型付きエラーを提供する。
"""

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class FrontmatterMeta(BaseModel):
    """Markdown Frontmatter のメタデータスキーマ

    Attributes:
        domain: 検索ドメイン（Neo4j :Domain ノードに対応）
        tags: タグリスト（Neo4j :Tag ノードに対応）
        title: ドキュメントタイトル（未指定時は source_file のステム）
        created_at: 変換日時（ISO 8601）
        source_file: 元ファイル名（Neo4j :SourceDocument ノードに対応）
    """

    domain: str = "general"
    tags: list[str] = Field(default_factory=list)
    title: str | None = None
    created_at: str
    source_file: str

    @model_validator(mode="after")
    def ensure_title(self) -> "FrontmatterMeta":
        if self.title is None or self.title.strip() == "":
            self.title = Path(self.source_file).stem or "untitled"
        return self


class LocalDocumentInput(BaseModel):
    """Local Doc Loader の単一入力。"""

    filename: str
    file_bytes: bytes
    domain: str = "general"
    tags: list[str] = Field(default_factory=list)
    title: str | None = None


class LocalDocumentOutput(BaseModel):
    """Local Doc Loader の単一出力。"""

    mime: str
    markdown: str
    meta: FrontmatterMeta


class LocalDocLoaderErrorType(StrEnum):
    """Local Doc Loader のエラー分類。"""

    UNSUPPORTED_MIME = "unsupported_mime"
    CONVERSION_FAILED = "conversion_failed"
    TEXT_DECODE_FAILED = "text_decode_failed"
    FRONTMATTER_PARSE_FAILED = "frontmatter_parse_failed"
    CLEANING_FAILED = "cleaning_failed"


class LocalDocLoaderError(Exception):
    """Local Doc Loader の基底例外。"""

    def __init__(
        self,
        *,
        error_type: LocalDocLoaderErrorType,
        filename: str,
        detail: str,
        mime: str | None = None,
    ) -> None:
        self.error_type = error_type
        self.filename = filename
        self.mime = mime
        self.detail = detail
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        mime_label = self.mime if self.mime is not None else "unknown"
        return f"[{self.error_type}] file={self.filename} mime={mime_label} detail={self.detail}"


class UnsupportedMimeTypeError(LocalDocLoaderError):
    def __init__(self, *, filename: str, mime: str, detail: str) -> None:
        super().__init__(
            error_type=LocalDocLoaderErrorType.UNSUPPORTED_MIME,
            filename=filename,
            mime=mime,
            detail=detail,
        )


class DocumentConversionError(LocalDocLoaderError):
    def __init__(self, *, filename: str, mime: str, detail: str) -> None:
        super().__init__(
            error_type=LocalDocLoaderErrorType.CONVERSION_FAILED,
            filename=filename,
            mime=mime,
            detail=detail,
        )


class TextDecodingError(LocalDocLoaderError):
    def __init__(self, *, filename: str, mime: str, detail: str) -> None:
        super().__init__(
            error_type=LocalDocLoaderErrorType.TEXT_DECODE_FAILED,
            filename=filename,
            mime=mime,
            detail=detail,
        )


class FrontmatterParseError(LocalDocLoaderError):
    def __init__(self, *, filename: str, detail: str) -> None:
        super().__init__(
            error_type=LocalDocLoaderErrorType.FRONTMATTER_PARSE_FAILED,
            filename=filename,
            detail=detail,
        )


class MarkdownCleaningError(LocalDocLoaderError):
    def __init__(self, *, filename: str, detail: str) -> None:
        super().__init__(
            error_type=LocalDocLoaderErrorType.CLEANING_FAILED,
            filename=filename,
            detail=detail,
        )

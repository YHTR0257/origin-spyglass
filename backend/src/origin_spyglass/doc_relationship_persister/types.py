"""Doc Relationship Persister の型定義"""

from datetime import date

from pydantic import BaseModel, Field

from origin_spyglass.local_doc_loader.types import LocalDocumentOutput
from origin_spyglass.schemas.doc_relation import SourceType


class MetadataValidationError(ValueError):
    """メタデータバリデーションエラー"""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"[validation] field={field} reason={reason}")


class DuplicateDocumentError(ValueError):
    """重複ドキュメントエラー（同一 title + 年のドキュメントが既に存在する）"""

    def __init__(self, doc_id: str, title: str, year: int) -> None:
        self.doc_id = doc_id
        self.title = title
        self.year = year
        super().__init__(f"[duplicate] doc_id={doc_id} title={title!r} year={year}")


class VectorStoreUnavailable(Exception):
    """VectorStore（PostgreSQL）への接続不可を示す例外"""

    pass


class DocRelationshipPersisterInput(BaseModel):
    """Doc Relationship Persister の入力スキーマ

    Local Doc Loader の出力に追加メタデータを付与して永続化する。

    Attributes:
        document: Local Doc Loader の出力（Markdown 本文 + Frontmatter メタデータ）
        author: 著者名
        source_type: ドキュメントの取得元種別
        confidence: 確信度（0.0〜1.0）
        date: 公開・取得日
    """

    document: LocalDocumentOutput
    author: str
    source_type: SourceType
    confidence: float = Field(ge=0.0, le=1.0)
    date: date


class DocRelationshipPersisterOutput(BaseModel):
    """Doc Relationship Persister の出力スキーマ

    Attributes:
        doc_id: ドキュメント識別子（source_file のステムから生成）
        display_id: UI 表示向け識別子（内部 doc_id とは分離）
        title: ドキュメントタイトル
        source_file: 元ファイル名
        domain: 検索ドメイン
        tags: タグリスト
        author: 著者名
        source_type: ドキュメントの取得元種別
        confidence: 確信度（0.0〜1.0）
        date: 公開・取得日
        created_at: レコード作成日時（ISO 8601）
    """

    doc_id: str
    display_id: str
    title: str
    source_file: str
    domain: str
    tags: list[str]
    author: str
    source_type: SourceType
    confidence: float
    date: date
    created_at: str

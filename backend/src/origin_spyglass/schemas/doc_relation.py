"""doc-relation スキーマ定義

doc-relation はドキュメント間の引用関係を表す。
Neo4j グラフ上の edge とそのプロパティに対応する。

domain の値セットは将来的に PostgreSQL で管理する予定。
現時点では文字列として受け取り、呼び出し側でバリデーションを行う。
"""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    LOCAL_MARKDOWN = "local_markdown"
    LOCAL_PDF = "local_pdf"
    WEB = "web"
    API = "api"
    IMAGE = "image"


class DocRelation(BaseModel):
    """ドキュメント間の引用関係を表すスキーマ

    Attributes:
        tags: ドキュメントに付与されたタグリスト
        author: 著者名
        source_type: ドキュメントの取得元種別
        confidence: 関係の確信度（0.0〜1.0）
        date: 公開・取得日（年月での範囲検索に対応）
        domain: 検索ドメイン（将来的に PostgreSQL で管理）
    """

    tags: list[str] = Field(default_factory=list)
    author: str
    source_type: SourceType
    confidence: float = Field(ge=0.0, le=1.0)
    date: date
    domain: str = Field(
        description="検索ドメイン。将来的に PostgreSQL のマスタテーブルで管理する。"
    )

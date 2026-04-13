"""semantic-knowledge スキーマ定義

semantic_knowledge は意味ベースの関連付けがなされた単語群を表す。
それぞれは意味を持つ小さな節であり、相互に関連性を持つ。

domain の値セットは将来的に PostgreSQL で管理する予定。
現時点では文字列として受け取り、呼び出し側でバリデーションを行う。
"""

from pydantic import BaseModel, Field


class SemanticKnowledge(BaseModel):
    """意味ベースの関連付けがなされた知識単位を表すスキーマ

    Attributes:
        domain: 検索ドメイン（将来的に PostgreSQL で管理）
        doc_id: 参照元の doc-relation ドキュメント ID
    """

    domain: str = Field(
        description="検索ドメイン。将来的に PostgreSQL のマスタテーブルで管理する。"
    )
    doc_id: str = Field(description="参照元の doc-relation ドキュメント ID")

"""IdeaRelationPersister の入出力スキーマ・エラー型定義"""

from datetime import date

from pydantic import BaseModel, Field

from origin_spyglass.local_doc_loader.types import FrontmatterMeta
from origin_spyglass.schemas.doc_relation import SourceType


class IdeaFrontmatterMeta(FrontmatterMeta):
    """IdeaRelationPersister 専用の Frontmatter メタデータ。

    FrontmatterMeta に source_type / confidence / date を追加する。
    """

    source_type: SourceType
    confidence: float = Field(ge=0.0, le=1.0)
    date: date


class IdeaRelationPersisterInput(BaseModel):
    """IdeaRelationPersister への入力スキーマ。"""

    doc_id: str
    frontmatter: IdeaFrontmatterMeta
    body_text: str
    chunk_size: int = Field(default=256, ge=64, le=4096)
    chunk_overlap: int = Field(default=32, ge=0)
    show_progress: bool = False


# STEP1 バリデーション通過後の型エイリアス（再構築なし）
ValidatedIdeaRelationInput = IdeaRelationPersisterInput


class IdeaRelationPersisterOutput(BaseModel):
    """IdeaRelationPersister からの出力スキーマ。"""

    doc_id: str
    persisted: bool
    node_count: int
    edge_count: int
    elapsed_ms: int
    warnings: list[str] = Field(default_factory=list)


# --- エラー型 ---


class IdeaRelationValidationError(ValueError):
    """入力バリデーション失敗を表すエラー。"""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"[validation] field={field} reason={reason}")


class GraphStoreUnavailable(Exception):
    """Neo4j ストアへの接続が不可能な場合に raise する。"""


class ExtractionFailed(Exception):
    """LLM トリプレット抽出が失敗した場合に raise する。"""


class PersistFailed(Exception):
    """Neo4j への upsert 操作が失敗した場合に raise する。"""

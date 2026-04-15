"""IdeaRelationRetriever の入出力スキーマ・エラー型定義"""

from pydantic import BaseModel, Field


class IdeaRelationRetrieverInput(BaseModel):
    """IdeaRelationRetriever への入力スキーマ。"""

    question: str
    max_results: int = Field(default=10, ge=1, le=100)
    domain: str | None = None
    user_id: str | None = None


# STEP1 バリデーション通過後の型エイリアス（再構築なし）
ValidatedInput = IdeaRelationRetrieverInput


class RelatedIdea(BaseModel):
    """関連アイデアの単一エントリ。"""

    node_id: str
    title: str
    body_snippet: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class IdeaRelationRetrieverOutput(BaseModel):
    """IdeaRelationRetriever からの出力スキーマ。"""

    question: str
    answer: str
    related_ideas: list[RelatedIdea]
    elapsed_ms: int
    warnings: list[str] = Field(default_factory=list)


# --- エラー型 ---


class IdeaRelationRetrieverValidationError(ValueError):
    """入力バリデーション失敗を表すエラー。"""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"[validation] field={field} reason={reason}")


class QueryFailed(Exception):
    """LLM 意図解析またはグラフクエリ実行が失敗した場合に raise する。"""

"""Doc Retriever ノードの入出力スキーマと例外型定義"""

from pydantic import BaseModel, Field

# ============================================================================
# 共通スキーマ
# ============================================================================


class RetrievedDoc(BaseModel):
    """検索結果のドキュメント情報"""

    node_id: str = Field(description="ドキュメントの内部ID")
    title: str = Field(description="ドキュメントタイトル")
    body_snippet: str = Field(description="本文の抜粋（最大300文字）")
    relevance_score: float = Field(ge=0.0, le=1.0, description="関連度スコア（0.0～1.0）")


# ============================================================================
# 例外型
# ============================================================================


class DocRetrieverValidationError(ValueError):
    """入力バリデーションエラー"""

    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(f"[validation] field={field} reason={reason}")


class QueryFailed(Exception):
    """LLM  呼び出し失敗またはクエリ実行失敗"""

    pass


# ============================================================================
# retrieval_with_text 関連
# ============================================================================


class DocTextRetrieverInput(BaseModel):
    """自然言語質問による検索の入力スキーマ"""

    question: str = Field(description="自然言語の質問文")
    max_results: int = Field(default=10, ge=1, le=100, description="返すドキュメントの最大数")
    domain: str | None = Field(default=None, description="検索対象ドメインのフィルタ（オプション）")
    user_id: str | None = Field(default=None, description="質問者の識別子（ログ用）")


ValidatedTextInput = DocTextRetrieverInput


class DocTextRetrieverOutput(BaseModel):
    """自然言語質問による検索の出力スキーマ"""

    question: str = Field(description="入力された質問文")
    answer: str = Field(description="LLMが生成した回答文")
    related_docs: list[RetrievedDoc] = Field(
        description="関連ドキュメントのリスト（0件の場合は空リスト）"
    )
    elapsed_ms: int = Field(description="処理時間（ms）")
    warnings: list[str] = Field(
        default_factory=list, description="軽微な警告（best-effort処理の失敗など）"
    )


# ============================================================================
# retrieval_with_keywords 関連
# ============================================================================


class DocKeywordsRetrieverInput(BaseModel):
    """キーワードリストによる検索の入力スキーマ"""

    keywords: list[str] = Field(description="検索キーワードのリスト（1件以上）")
    max_results: int = Field(default=10, ge=1, le=100, description="返すドキュメントの最大数")
    domain: str | None = Field(default=None, description="検索対象ドメインのフィルタ（オプション）")
    user_id: str | None = Field(default=None, description="質問者の識別子（ログ用）")


ValidatedKeywordsInput = DocKeywordsRetrieverInput


class DocKeywordsRetrieverOutput(BaseModel):
    """キーワードリストによる検索の出力スキーマ"""

    keywords: list[str] = Field(description="入力されたキーワードリスト")
    answer: str = Field(description="LLMが生成した回答文")
    related_docs: list[RetrievedDoc] = Field(
        description="関連ドキュメントのリスト（0件の場合は空リスト）"
    )
    elapsed_ms: int = Field(description="処理時間（ms）")
    warnings: list[str] = Field(
        default_factory=list, description="軽微な警告（best-effort処理の失敗など）"
    )


# ============================================================================
# retrieval_with_doc_ids 関連
# ============================================================================


class DocIdsRetrieverInput(BaseModel):
    """ドキュメントIDリストによる検索の入力スキーマ"""

    doc_ids: list[str] = Field(description="取得するドキュメントIDのリスト（1件以上）")
    user_id: str | None = Field(default=None, description="質問者の識別子（ログ用）")


ValidatedIdsInput = DocIdsRetrieverInput


class DocIdsRetrieverOutput(BaseModel):
    """ドキュメントIDリストによる検索の出力スキーマ"""

    doc_ids: list[str] = Field(description="入力されたドキュメントIDリスト")
    answer: str = Field(description="LLMが生成した回答文（取得ドキュメントのサマリー）")
    related_docs: list[RetrievedDoc] = Field(
        description="取得ドキュメントのリスト（0件の場合は空リスト）"
    )
    elapsed_ms: int = Field(description="処理時間（ms）")
    warnings: list[str] = Field(
        default_factory=list, description="軽微な警告（best-effort処理の失敗など）"
    )

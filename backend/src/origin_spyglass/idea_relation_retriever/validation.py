"""STEP1: 入力バリデーション"""

from .types import IdeaRelationRetrieverInput, IdeaRelationRetrieverValidationError, ValidatedInput


def validate(input: IdeaRelationRetrieverInput) -> ValidatedInput:
    """入力を検証し、バリデーション済み入力を返す。

    最初の違反で即座に raise する（fail-fast）。
    max_results の範囲チェックは Pydantic Field(ge=1, le=100) がカバーするため省略。

    Args:
        input: バリデーション前の入力

    Returns:
        ValidatedInput: バリデーション通過後の入力（型エイリアス）

    Raises:
        IdeaRelationRetrieverValidationError: バリデーション失敗時
    """
    if not input.question.strip():
        raise IdeaRelationRetrieverValidationError("question", "must not be empty or whitespace")

    if input.domain is not None and not input.domain.strip():
        raise IdeaRelationRetrieverValidationError(
            "domain", "must not be empty or whitespace when specified"
        )

    return input

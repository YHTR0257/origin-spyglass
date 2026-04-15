"""STEP1: 入力バリデーション"""

from .types import (
    DocIdsRetrieverInput,
    DocKeywordsRetrieverInput,
    DocRetrieverValidationError,
    DocTextRetrieverInput,
    ValidatedIdsInput,
    ValidatedKeywordsInput,
    ValidatedTextInput,
)


def validate_text(input_data: DocTextRetrieverInput) -> ValidatedTextInput:
    """テキスト入力（質問）のバリデーション

    Args:
        input_data: 入力スキーマ

    Returns:
        バリデーション済みの入力スキーマ

    Raises:
        DocRetrieverValidationError: バリデーション失敗時
    """
    # question: 非空、空白のみ禁止
    if not input_data.question or not input_data.question.strip():
        raise DocRetrieverValidationError("question", "必須かつ空白のみは不可")

    # max_results: 1 <= x <= 100
    if not (1 <= input_data.max_results <= 100):
        raise DocRetrieverValidationError("max_results", "1～100の範囲で指定してください")

    # domain: 指定時は非空・空白のみ禁止
    if input_data.domain is not None and not input_data.domain.strip():
        raise DocRetrieverValidationError("domain", "空白のみは不可")

    return input_data


def validate_keywords(input_data: DocKeywordsRetrieverInput) -> ValidatedKeywordsInput:
    """キーワードリスト入力のバリデーション

    Args:
        input_data: 入力スキーマ

    Returns:
        バリデーション済みの入力スキーマ

    Raises:
        DocRetrieverValidationError: バリデーション失敗時
    """
    # keywords: 1件以上、各要素が非空・空白のみ禁止
    if not input_data.keywords:
        raise DocRetrieverValidationError("keywords", "1件以上必須")

    for i, keyword in enumerate(input_data.keywords):
        if not keyword or not keyword.strip():
            raise DocRetrieverValidationError("keywords", f"要素 {i}: 非空かつ空白のみは不可")

    # max_results: 1 <= x <= 100
    if not (1 <= input_data.max_results <= 100):
        raise DocRetrieverValidationError("max_results", "1～100の範囲で指定してください")

    # domain: 指定時は非空・空白のみ禁止
    if input_data.domain is not None and not input_data.domain.strip():
        raise DocRetrieverValidationError("domain", "空白のみは不可")

    return input_data


def validate_doc_ids(input_data: DocIdsRetrieverInput) -> ValidatedIdsInput:
    """ドキュメントIDリスト入力のバリデーション

    Args:
        input_data: 入力スキーマ

    Returns:
        バリデーション済みの入力スキーマ

    Raises:
        DocRetrieverValidationError: バリデーション失敗時
    """
    # doc_ids: 1件以上、各要素が非空
    if not input_data.doc_ids:
        raise DocRetrieverValidationError("doc_ids", "1件以上必須")

    for i, doc_id in enumerate(input_data.doc_ids):
        if not doc_id or not isinstance(doc_id, str):
            raise DocRetrieverValidationError("doc_ids", f"要素 {i}: 非空かつ文字列必須")

    return input_data

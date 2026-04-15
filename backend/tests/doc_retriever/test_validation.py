"""STEP1: 入力バリデーション テスト"""

import pytest

from origin_spyglass.doc_retriever import (
    DocKeywordsRetrieverInput,
    DocRetrieverValidationError,
    DocTextRetrieverInput,
)
from origin_spyglass.doc_retriever.validation import (
    validate_doc_ids,
    validate_keywords,
    validate_text,
)

from ._helpers import (
    make_ids_input,
    make_keywords_input,
    make_text_input,
)


class TestValidateText:
    """validate_text のテスト"""

    def test_normal_question(self) -> None:
        """通常の質問がバリデーション通過"""
        input_data = make_text_input()
        result = validate_text(input_data)
        assert result == input_data

    def test_empty_question(self) -> None:
        """空文字の質問でエラー"""
        input_data = make_text_input(question="")
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_text(input_data)
        assert exc_info.value.field == "question"

    def test_whitespace_only_question(self) -> None:
        """空白のみの質問でエラー"""
        input_data = make_text_input(question="   ")
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_text(input_data)
        assert exc_info.value.field == "question"

    def test_max_results_below_min(self) -> None:
        """max_results < 1でエラー
        （Pydantic バリデーションをバイパスして検証ロジックを直接テスト）"""
        input_data = DocTextRetrieverInput.model_construct(
            question="量子コンピュータとは？",
            max_results=0,
            domain=None,
            user_id=None,
        )
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_text(input_data)
        assert exc_info.value.field == "max_results"

    def test_max_results_above_max(self) -> None:
        """max_results > 100でエラー
        （Pydantic バリデーションをバイパスして検証ロジックを直接テスト）"""
        input_data = DocTextRetrieverInput.model_construct(
            question="量子コンピュータとは？",
            max_results=101,
            domain=None,
            user_id=None,
        )
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_text(input_data)
        assert exc_info.value.field == "max_results"

    def test_domain_whitespace_only(self) -> None:
        """domain が空白のみでエラー"""
        input_data = make_text_input(domain="  ")
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_text(input_data)
        assert exc_info.value.field == "domain"

    def test_domain_none_ok(self) -> None:
        """domain が None でOK"""
        input_data = make_text_input(domain=None)
        result = validate_text(input_data)
        assert result.domain is None

    def test_domain_valid(self) -> None:
        """domain が有効でOK"""
        input_data = make_text_input(domain="research")
        result = validate_text(input_data)
        assert result.domain == "research"


class TestValidateKeywords:
    """validate_keywords のテスト"""

    def test_normal_keywords(self) -> None:
        """通常のキーワードリストがバリデーション通過"""
        input_data = make_keywords_input()
        result = validate_keywords(input_data)
        assert result == input_data

    def test_empty_keywords_list(self) -> None:
        """キーワードリストが空でエラー"""
        input_data = make_keywords_input(keywords=[])
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_keywords(input_data)
        assert exc_info.value.field == "keywords"

    def test_keyword_with_empty_element(self) -> None:
        """キーワードに空文字要素があるとエラー"""
        input_data = make_keywords_input(keywords=["quantum", "", "computer"])
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_keywords(input_data)
        assert exc_info.value.field == "keywords"

    def test_keyword_with_whitespace_element(self) -> None:
        """キーワードに空白のみの要素があるとエラー"""
        input_data = make_keywords_input(keywords=["quantum", "  ", "computer"])
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_keywords(input_data)
        assert exc_info.value.field == "keywords"

    def test_keywords_max_results_below_min(self) -> None:
        """max_results < 1でエラー
        （Pydantic バリデーションをバイパスして検証ロジックを直接テスト）"""
        input_data = DocKeywordsRetrieverInput.model_construct(
            keywords=["quantum"],
            max_results=0,
            domain=None,
            user_id=None,
        )
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_keywords(input_data)
        assert exc_info.value.field == "max_results"

    def test_keywords_max_results_above_max(self) -> None:
        """max_results > 100でエラー
        （Pydantic バリデーションをバイパスして検証ロジックを直接テスト）"""
        input_data = DocKeywordsRetrieverInput.model_construct(
            keywords=["quantum"],
            max_results=101,
            domain=None,
            user_id=None,
        )
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_keywords(input_data)
        assert exc_info.value.field == "max_results"

    def test_keywords_domain_whitespace_only(self) -> None:
        """domain が空白のみでエラー"""
        input_data = make_keywords_input(domain="  ")
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_keywords(input_data)
        assert exc_info.value.field == "domain"

    def test_keywords_single_keyword_ok(self) -> None:
        """単一のキーワードでOK"""
        input_data = make_keywords_input(keywords=["quantum"])
        result = validate_keywords(input_data)
        assert result.keywords == ["quantum"]


class TestValidateDocIds:
    """validate_doc_ids のテスト"""

    def test_normal_doc_ids(self) -> None:
        """通常のドキュメントIDリストがバリデーション通過"""
        input_data = make_ids_input()
        result = validate_doc_ids(input_data)
        assert result == input_data

    def test_empty_doc_ids_list(self) -> None:
        """ドキュメントIDリストが空でエラー"""
        input_data = make_ids_input(doc_ids=[])
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_doc_ids(input_data)
        assert exc_info.value.field == "doc_ids"

    def test_doc_id_with_empty_element(self) -> None:
        """ドキュメントIDに空文字要素があるとエラー"""
        input_data = make_ids_input(doc_ids=["550e8400-e29b-41d4-a716-446655440000", ""])
        with pytest.raises(DocRetrieverValidationError) as exc_info:
            validate_doc_ids(input_data)
        assert exc_info.value.field == "doc_ids"

    def test_doc_ids_single_id_ok(self) -> None:
        """単一のドキュメントIDでOK"""
        input_data = make_ids_input(doc_ids=["550e8400-e29b-41d4-a716-446655440000"])
        result = validate_doc_ids(input_data)
        assert len(result.doc_ids) == 1

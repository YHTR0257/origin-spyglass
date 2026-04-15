"""validation.py のテスト"""

import pytest

from origin_spyglass.idea_relation_retriever.types import IdeaRelationRetrieverValidationError
from origin_spyglass.idea_relation_retriever.validation import validate

from ._helpers import make_valid_input


class TestValidateHappyPath:
    def test_valid_input_passes(self) -> None:
        input_ = make_valid_input()
        result = validate(input_)
        assert result is input_

    def test_valid_input_with_domain_passes(self) -> None:
        input_ = make_valid_input(domain="コンピュータサイエンス")
        result = validate(input_)
        assert result is input_

    def test_valid_input_with_user_id_passes(self) -> None:
        input_ = make_valid_input(user_id="user-123")
        result = validate(input_)
        assert result is input_

    def test_max_results_boundary_min(self) -> None:
        input_ = make_valid_input(max_results=1)
        assert validate(input_) is input_

    def test_max_results_boundary_max(self) -> None:
        input_ = make_valid_input(max_results=100)
        assert validate(input_) is input_


class TestValidateQuestion:
    def test_empty_question_raises(self) -> None:
        input_ = make_valid_input(question="")
        with pytest.raises(IdeaRelationRetrieverValidationError) as exc_info:
            validate(input_)
        assert exc_info.value.field == "question"

    def test_whitespace_only_question_raises(self) -> None:
        input_ = make_valid_input(question="   ")
        with pytest.raises(IdeaRelationRetrieverValidationError) as exc_info:
            validate(input_)
        assert exc_info.value.field == "question"

    def test_newline_only_question_raises(self) -> None:
        input_ = make_valid_input(question="\n\t")
        with pytest.raises(IdeaRelationRetrieverValidationError) as exc_info:
            validate(input_)
        assert exc_info.value.field == "question"


class TestValidateDomain:
    def test_none_domain_passes(self) -> None:
        input_ = make_valid_input(domain=None)
        assert validate(input_) is input_

    def test_empty_domain_raises(self) -> None:
        input_ = make_valid_input(domain="")
        with pytest.raises(IdeaRelationRetrieverValidationError) as exc_info:
            validate(input_)
        assert exc_info.value.field == "domain"

    def test_whitespace_only_domain_raises(self) -> None:
        input_ = make_valid_input(domain="  ")
        with pytest.raises(IdeaRelationRetrieverValidationError) as exc_info:
            validate(input_)
        assert exc_info.value.field == "domain"

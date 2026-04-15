"""interpret.py のテスト"""

from unittest.mock import MagicMock

import pytest

from origin_spyglass.idea_relation_retriever.interpret import interpret_question
from origin_spyglass.idea_relation_retriever.types import QueryFailed


class TestInterpretQuestion:
    def test_returns_refined_query_string(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = MagicMock(text="量子コンピュータ 古典コンピュータ 比較 関係")

        result = interpret_question("量子コンピュータと古典コンピュータの関係は？", llm)

        assert result == "量子コンピュータ 古典コンピュータ 比較 関係"
        llm.complete.assert_called_once()

    def test_strips_whitespace_from_result(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = MagicMock(text="  キーワード1 キーワード2  \n")

        result = interpret_question("テスト質問", llm)

        assert result == "キーワード1 キーワード2"

    def test_domain_hint_included_in_prompt(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = MagicMock(text="量子コンピュータ")

        interpret_question("量子とは？", llm, domain="物理学")

        prompt_arg: str = llm.complete.call_args[0][0]
        assert "物理学" in prompt_arg

    def test_no_domain_hint_when_domain_is_none(self) -> None:
        llm = MagicMock()
        llm.complete.return_value = MagicMock(text="キーワード")

        interpret_question("質問", llm, domain=None)

        prompt_arg: str = llm.complete.call_args[0][0]
        assert "ドメイン" not in prompt_arg

    def test_llm_exception_raises_query_failed(self) -> None:
        llm = MagicMock()
        llm.complete.side_effect = RuntimeError("LLM timeout")

        with pytest.raises(QueryFailed):
            interpret_question("質問", llm)

    def test_query_failed_wraps_original_exception(self) -> None:
        original_error = ConnectionError("connection refused")
        llm = MagicMock()
        llm.complete.side_effect = original_error

        with pytest.raises(QueryFailed) as exc_info:
            interpret_question("質問", llm)

        assert exc_info.value.__cause__ is original_error

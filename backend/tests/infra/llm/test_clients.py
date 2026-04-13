import pytest

from origin_spyglass.infra.llm.clients import LlmClientFactory, LlmClientManager, LlmProvider


def test_normalize_provider_accepts_openai_aliases() -> None:
    assert LlmClientFactory._normalize_provider("openai") == LlmProvider.OPENAI_API
    assert LlmClientFactory._normalize_provider("openai_api") == LlmProvider.OPENAI_API
    assert LlmClientFactory._normalize_provider("openai-compatible") == LlmProvider.OPENAI_API


def test_normalize_provider_rejects_non_openai() -> None:
    with pytest.raises(ValueError, match="OpenAI API 形式のみ"):
        LlmClientFactory._normalize_provider("anthropic")


def test_make_key_normalizes_provider_aliases() -> None:
    key = LlmClientManager._make_key("openai", "gpt-4o-mini")
    assert key == "openai_api:gpt-4o-mini"

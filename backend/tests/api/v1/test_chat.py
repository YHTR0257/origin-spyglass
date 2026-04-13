import pytest
from fastapi.testclient import TestClient

from origin_spyglass.main import app

client = TestClient(app)

VALID_REQUEST = {
    "model": "llm-agent",
    "messages": [{"role": "user", "content": "Hello"}],
}


# ---------------------------------------------------------------------------
# 正常系
# ---------------------------------------------------------------------------


def test_chat_completions_ok() -> None:
    response = client.post("/v1/chat/completions", json=VALID_REQUEST)
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "llm-agent"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert "id" in data
    assert "created" in data
    assert "usage" in data


def test_chat_completions_with_system_message() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llm-agent",
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
            ],
        },
    )
    assert response.status_code == 200


def test_chat_completions_two_identical_messages_allowed() -> None:
    # 2 repeats is not a loop — only 3+ should be rejected
    messages = [{"role": "user", "content": "same"}] * 2
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llm-agent", "messages": messages},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 異常系 — リクエスト形式
# ---------------------------------------------------------------------------


def test_chat_completions_missing_model() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 422


def test_chat_completions_missing_messages() -> None:
    response = client.post("/v1/chat/completions", json={"model": "llm-agent"})
    assert response.status_code == 422


def test_chat_completions_invalid_role() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llm-agent", "messages": [{"role": "invalid", "content": "Hello"}]},
    )
    assert response.status_code == 422


def test_chat_completions_missing_message_content() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llm-agent", "messages": [{"role": "user"}]},
    )
    assert response.status_code == 422


def test_chat_completions_empty_body() -> None:
    response = client.post("/v1/chat/completions", json={})
    assert response.status_code == 422


@pytest.mark.parametrize("method", ["get", "put", "delete", "patch"])
def test_chat_completions_method_not_allowed(method: str) -> None:
    response = getattr(client, method)("/v1/chat/completions")
    assert response.status_code == 405


# ---------------------------------------------------------------------------
# 異常系 — 入力制限 (DoS / ループ対策)
# ---------------------------------------------------------------------------


def test_chat_empty_messages_rejected() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llm-agent", "messages": []},
    )
    assert response.status_code == 422


def test_chat_too_many_messages_rejected() -> None:
    messages = [{"role": "user", "content": "Hello"}] * 101
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llm-agent", "messages": messages},
    )
    assert response.status_code == 422


def test_chat_content_too_long_rejected() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llm-agent",
            "messages": [{"role": "user", "content": "x" * 10_001}],
        },
    )
    assert response.status_code == 422


def test_chat_loop_detection_rejected() -> None:
    repeated = [{"role": "user", "content": "repeat this forever"}] * 3
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llm-agent", "messages": repeated},
    )
    assert response.status_code == 422


def test_chat_max_tokens_over_limit_rejected() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={**VALID_REQUEST, "max_tokens": 9999},
    )
    assert response.status_code == 422

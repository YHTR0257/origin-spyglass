from fastapi.testclient import TestClient

from origin_spyglass.main import app

client = TestClient(app)


def test_csp_header_present() -> None:
    response = client.get("/v1/health")
    csp = response.headers.get("Content-Security-Policy", "")
    assert "script-src" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp


def test_x_content_type_options_header() -> None:
    response = client.get("/v1/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_x_frame_options_header() -> None:
    response = client.get("/v1/health")
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_referrer_policy_header() -> None:
    response = client.get("/v1/health")
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_security_headers_applied_to_chat_endpoint() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llm-agent", "messages": [{"role": "user", "content": "Hello"}]},
    )
    assert "Content-Security-Policy" in response.headers
    assert response.headers.get("X-Frame-Options") == "DENY"

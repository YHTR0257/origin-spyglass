import logging

import pytest

from spyglass_utils.output_filter import check_sensitive, sanitize

# ---------------------------------------------------------------------------
# sanitize — HTML エスケープ
# ---------------------------------------------------------------------------


def test_sanitize_escapes_script_tag() -> None:
    result = sanitize("<script>alert('xss')</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_sanitize_escapes_img_onerror() -> None:
    result = sanitize("<img src=x onerror=alert(1)>")
    assert "<img" not in result
    assert "&lt;img" in result


def test_sanitize_escapes_ampersand() -> None:
    assert sanitize("a & b") == "a &amp; b"


def test_sanitize_passes_plain_text() -> None:
    text = "Hello, this is a normal response."
    assert sanitize(text) == text


# ---------------------------------------------------------------------------
# check_sensitive — シークレット / PII 検知
# ---------------------------------------------------------------------------


def test_blocks_openai_key() -> None:
    with pytest.raises(ValueError, match="openai_key"):
        check_sensitive("sk-" + "a" * 30)


def test_blocks_aws_access_key() -> None:
    with pytest.raises(ValueError, match="aws_access_key"):
        check_sensitive("AKIAIOSFODNN7EXAMPLE")


def test_blocks_private_key_header() -> None:
    with pytest.raises(ValueError, match="private_key"):
        check_sensitive("-----BEGIN RSA PRIVATE KEY-----\nMIIE...")


def test_passes_clean_text() -> None:
    check_sensitive("Hello! This is a normal response.")


def test_warns_on_email(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="utils.output_filter"):
        check_sensitive("contact: user@example.com")
    assert any("email" in record.message for record in caplog.records)

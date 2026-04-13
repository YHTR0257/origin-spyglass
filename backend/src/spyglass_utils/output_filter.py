import html
import re

from spyglass_utils.logging import get_logger

logger = get_logger(__name__)

# Patterns checked against LLM output.
# _BLOCK_PATTERNS: high-confidence secret leaks — response is blocked.
# Others: log a warning but allow through.
_PATTERNS: dict[str, re.Pattern[str]] = {
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
}

_BLOCK_PATTERNS: frozenset[str] = frozenset({"openai_key", "aws_access_key", "private_key"})


def check_sensitive(text: str) -> None:
    """Scan text for sensitive patterns.

    Raises ValueError for high-confidence secret leaks.
    Logs a warning for softer PII matches (email, credit card).
    """
    for name, pattern in _PATTERNS.items():
        if pattern.search(text):
            if name in _BLOCK_PATTERNS:
                raise ValueError(f"output contains potential secret ({name})")
            logger.warning("potential PII detected in LLM output: %s", name)


def sanitize(text: str) -> str:
    """HTML-escape text to prevent XSS when rendered in a browser."""
    return html.escape(text)

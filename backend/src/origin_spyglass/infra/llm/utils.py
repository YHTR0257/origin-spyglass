"""LLM例外マッピングユーティリティ"""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from .exceptions import (
    LlmAuthenticationError,
    LlmConnectionError,
    LlmRateLimitError,
    LlmResponseParseError,
    LlmTimeoutError,
)

T = TypeVar("T")


def map_llm_exceptions(func: Callable[..., T]) -> Callable[..., T]:
    """プロバイダー例外をカスタム例外にマッピングするデコレータ

    Args:
        func: ラップする関数

    Returns:
        例外マッピングを行うラッパー関数
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except (
            LlmAuthenticationError,
            LlmRateLimitError,
            LlmTimeoutError,
            LlmConnectionError,
            LlmResponseParseError,
        ):
            # カスタム例外はそのまま再送出
            raise
        except Exception as e:
            error_name = type(e).__name__.lower()
            error_str = str(e).lower()

            # 認証エラー
            if "authentication" in error_name or "unauthenticated" in error_str:
                raise LlmAuthenticationError(f"認証エラー: {e}") from e

            # クレジット不足・Billingエラー（Anthropic: BadRequestError として届く）
            if "credit" in error_str or "balance" in error_str or "billing" in error_str:
                raise LlmRateLimitError(f"クレジット不足またはBillingエラー: {e}") from e

            # レートリミット
            if "ratelimit" in error_name or "quota" in error_str:
                raise LlmRateLimitError(f"レートリミット: {e}") from e

            # タイムアウト
            if "timeout" in error_name:
                raise LlmTimeoutError(f"タイムアウト: {e}") from e

            # 接続エラー
            if "connection" in error_name or "connect" in error_str:
                raise LlmConnectionError(f"接続エラー: {e}") from e

            # パースエラー
            if "validation" in error_name or "json" in error_name:
                raise LlmResponseParseError(f"パースエラー: {e}") from e

            # その他の例外
            raise LlmConnectionError(f"予期しないエラー: {e}") from e

    return wrapper

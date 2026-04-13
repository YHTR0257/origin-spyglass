"""LLM関連の例外クラス"""


class LlmError(Exception):
    """LLM関連エラーの基底クラス"""

    pass


class LlmConnectionError(LlmError):
    """LLMサービスへの接続エラー"""

    pass


class LlmAuthenticationError(LlmError):
    """認証エラー（無効なAPIキー等）"""

    pass


class LlmRateLimitError(LlmError):
    """レートリミット超過エラー"""

    pass


class LlmTimeoutError(LlmError):
    """タイムアウトエラー"""

    pass


class LlmResponseParseError(LlmError):
    """レスポンスのパースエラー"""

    pass

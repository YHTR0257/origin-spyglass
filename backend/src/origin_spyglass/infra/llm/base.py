from abc import ABC, abstractmethod
from typing import TypeVar

from llama_index.core.llms import LLM
from pydantic import BaseModel

from .exceptions import LlmAuthenticationError, LlmResponseParseError
from .utils import map_llm_exceptions

T = TypeVar("T", bound=BaseModel)


class LlamaIndexLlmClient(ABC):
    """LlamaIndex LLM ラッパー

    すべてのLLMクライアントはこのクラスを継承し、
    health_checkメソッドを実装する必要があります。
    """

    def __init__(self, llm: LLM) -> None:
        """LlamaIndexLlmClientを初期化する

        Args:
            llm: LlamaIndex LLMインスタンス
        """
        self._llm = llm

    @property
    def llm(self) -> LLM:
        """LlamaIndex LLM インスタンスを取得する（RAG統合用）

        Returns:
            LlamaIndex LLMインスタンス
        """
        return self._llm

    @property
    def model(self) -> str:
        """使用中のモデル名を取得する

        Returns:
            モデル名
        """
        model_attr = getattr(self._llm, "model", None)
        if model_attr is None:
            return "unknown"
        return str(model_attr)

    @map_llm_exceptions
    def generate_response(self, prompt: str, response_model: type[T]) -> T:
        """プロンプトに基づいてLLMからレスポンスを生成する

        Args:
            prompt: LLMに送信する入力プロンプト
            response_model: レスポンスをパースするPydanticモデルクラス

        Returns:
            response_modelのインスタンス

        Raises:
            LlmAuthenticationError: 認証に失敗した場合
            LlmRateLimitError: レートリミットを超過した場合
            LlmConnectionError: 接続に失敗した場合
            LlmTimeoutError: タイムアウトした場合
            LlmResponseParseError: レスポンスのパースに失敗した場合
        """
        if self._llm is None:
            raise LlmAuthenticationError(
                "クライアントの初期化に失敗しました（APIキーまたはモデル名が無効）"
            )
        structured_llm = self._llm.as_structured_llm(response_model)
        response = structured_llm.complete(prompt)
        if response.raw is None:
            raise LlmResponseParseError("レスポンスにデータが含まれていません")
        return response.raw

    @abstractmethod
    def health_check(self) -> bool:
        """LLMサービスの接続状態を確認する

        Returns:
            接続が正常な場合はTrue、そうでない場合はFalse
        """
        pass

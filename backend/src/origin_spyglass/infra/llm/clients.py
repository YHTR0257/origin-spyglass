"""LLMクライアントファクトリー・マネージャー"""

from enum import Enum
from typing import Any, TypeVar, cast

from llama_index.core.llms import LLM
from pydantic import BaseModel

from .base import LlamaIndexLlmClient
from .exceptions import LlmConnectionError

T = TypeVar("T", bound=BaseModel)


class LlmProvider(str, Enum):
    """サポートされているLLMプロバイダー"""

    OPENAI_API = "openai_api"


class LlmClientFactory:
    """LLMクライアントのファクトリークラス

    プロバイダー名に基づいて適切なLLMクライアントを生成します。
    """

    @staticmethod
    def _normalize_provider(provider: LlmProvider | str) -> LlmProvider:
        """プロバイダー指定を OpenAI API 形式の単一サポートに正規化する。"""
        if isinstance(provider, LlmProvider):
            return provider

        normalized = provider.lower().strip()
        alias_map = {
            "openai": LlmProvider.OPENAI_API,
            "openai_api": LlmProvider.OPENAI_API,
            "openai-compatible": LlmProvider.OPENAI_API,
            "openai_compatible": LlmProvider.OPENAI_API,
        }
        mapped = alias_map.get(normalized)
        if mapped is None:
            raise ValueError(
                f"サポートされていないプロバイダー: {provider}. "
                "このスクリプトは OpenAI API 形式のみサポートします"
            )
        return mapped

    @staticmethod
    def create(provider: LlmProvider | str, **kwargs: Any) -> LlamaIndexLlmClient:
        """指定されたプロバイダーのLLMクライアントを生成する

        Args:
            provider: LLMプロバイダー名
            **kwargs: クライアント固有の設定パラメータ

        Returns:
            LlamaIndexLlmClientのインスタンス

        Raises:
            ValueError: サポートされていないプロバイダーの場合
        """
        provider = LlmClientFactory._normalize_provider(provider)

        if provider == LlmProvider.OPENAI_API:
            from .openai_api import OpenaiApiLlmClient

            return OpenaiApiLlmClient(**kwargs)

        raise ValueError(f"サポートされていないプロバイダー: {provider}")

    @staticmethod
    def create_embedding(provider: LlmProvider | str, **kwargs: Any) -> Any:
        """指定されたプロバイダーの埋め込みクライアントを生成する

        Args:
            provider: LLMプロバイダー名
            **kwargs: クライアント固有の設定パラメータ

        Returns:
            埋め込みクライアントのインスタンス

        Raises:
            ValueError: サポートされていないプロバイダーの場合
        """
        provider = LlmClientFactory._normalize_provider(provider)

        if provider == LlmProvider.OPENAI_API:
            from .openai_api import OpenaiApiEmbeddingClient

            return OpenaiApiEmbeddingClient(**kwargs)

        raise ValueError(f"埋め込みモデルがサポートされていないプロバイダー: {provider}")


class LlmClientManager:
    """複数のLLMクライアントを管理するマネージャークラス

    チャットLLMとembeddingクライアントを一元管理します。
    キーは "{provider}:{model}" 形式で、同一プロバイダーの複数モデルを区別できます。
    """

    def __init__(self) -> None:
        """LlmClientManagerを初期化する"""
        self._clients: dict[str, LlamaIndexLlmClient] = {}
        self._embedding_clients: dict[str, Any] = {}
        self._current_llm_key: str | None = None
        self._current_embedding_key: str | None = None

    @staticmethod
    def _make_key(provider: LlmProvider | str, model: str) -> str:
        """プロバイダーとモデル名からキーを生成する"""
        provider_str = LlmClientFactory._normalize_provider(provider).value
        return f"{provider_str}:{model}"

    def register(
        self,
        provider: LlmProvider | str,
        model: str,
        client: LlamaIndexLlmClient | None = None,
        **kwargs: Any,
    ) -> None:
        """チャットLLMクライアントを登録する

        Args:
            provider: LLMプロバイダー名
            model: モデル名
            client: 既存のクライアントインスタンス（Noneの場合は自動生成）
            **kwargs: クライアント生成時の設定パラメータ
        """
        key = self._make_key(provider, model)

        if client is None:
            client = LlmClientFactory.create(provider, model=model, **kwargs)

        self._clients[key] = client

        # 最初に登録されたクライアントをデフォルトとして設定
        if self._current_llm_key is None:
            self._current_llm_key = key

    def register_embedding(
        self,
        provider: LlmProvider | str,
        model_name: str,
        client: object | None = None,
        **kwargs: Any,
    ) -> None:
        """embeddingクライアントを登録する

        Args:
            provider: LLMプロバイダー名
            model_name: embeddingモデル名
            client: 既存のクライアントインスタンス（Noneの場合は自動生成）
            **kwargs: クライアント生成時の設定パラメータ
        """
        key = self._make_key(provider, model_name)

        if client is None:
            client = LlmClientFactory.create_embedding(provider, model_name=model_name, **kwargs)

        self._embedding_clients[key] = client

        # 最初に登録されたembeddingをデフォルトとして設定
        if self._current_embedding_key is None:
            self._current_embedding_key = key

    def select(self, provider: LlmProvider | str, model: str) -> None:
        """使用するクライアントを選択する

        provider:model のキーがチャットLLMまたはembeddingのどちらに
        登録されているかを自動判定して切り替えます。

        Args:
            provider: LLMプロバイダー名
            model: モデル名

        Raises:
            ValueError: 登録されていないキーの場合
        """
        key = self._make_key(provider, model)

        if key in self._clients:
            self._current_llm_key = key
        elif key in self._embedding_clients:
            self._current_embedding_key = key
        else:
            raise ValueError(f"'{key}' は登録されていません")

    def get_current_client(self) -> LlamaIndexLlmClient:
        """現在選択されているチャットLLMクライアントを取得する

        Returns:
            現在選択されているLlamaIndexLlmClientのインスタンス

        Raises:
            LlmConnectionError: クライアントが登録されていない場合
        """
        if self._current_llm_key is None or self._current_llm_key not in self._clients:
            raise LlmConnectionError("LLMクライアントが登録されていません")

        return self._clients[self._current_llm_key]

    def get_llm(self) -> LLM:
        """RAG統合用に LlamaIndex LLM を取得する

        Returns:
            llama_index.core.llms.LLM インスタンス
        """
        return self.get_current_client().llm

    def get_embed_model(self) -> Any:
        """現在選択されているembeddingモデルを取得する

        Returns:
            embeddingモデルインスタンス

        Raises:
            LlmConnectionError: embeddingクライアントが登録されていない場合
        """
        if (
            self._current_embedding_key is None
            or self._current_embedding_key not in self._embedding_clients
        ):
            raise LlmConnectionError("embeddingクライアントが登録されていません")

        client = self._embedding_clients[self._current_embedding_key]
        # embed_model プロパティがあればそれを返す
        embed_model = getattr(client, "embed_model", None)
        if embed_model is not None:
            return embed_model
        return client

    def generate_response(self, prompt: str, response_model: type[T]) -> T:
        """現在選択されているクライアントでレスポンスを生成する

        Args:
            prompt: LLMに送信する入力プロンプト
            response_model: レスポンスをパースするPydanticモデルクラス

        Returns:
            response_modelのインスタンス
        """
        client = self.get_current_client()
        return cast(T, client.generate_response(prompt, response_model))

    def health_check_embedding(self) -> bool:
        """現在選択されている embedding クライアントのヘルスチェックを実行する

        Returns:
            接続が正常な場合はTrue、登録なし・エラーの場合はFalse
        """
        if self._current_embedding_key is None:
            return False
        embed_client = self._embedding_clients.get(self._current_embedding_key)
        if embed_client is None:
            return False
        health_fn = getattr(embed_client, "health_check", None)
        if health_fn is not None:
            return bool(health_fn())
        return True

    def health_check(
        self, provider: LlmProvider | str | None = None, model: str | None = None
    ) -> bool:
        """指定されたキー（またはカレント）のヘルスチェックを実行する

        Args:
            provider: チェックするプロバイダー名（Noneの場合は現在のプロバイダー）
            model: チェックするモデル名（providerと一緒に指定）

        Returns:
            接続が正常な場合はTrue、そうでない場合はFalse
        """
        if provider is None:
            client = self.get_current_client()
            return client.health_check()

        if model is None:
            raise ValueError("provider を指定する場合は model も指定してください")

        key = self._make_key(provider, model)

        if key in self._clients:
            return self._clients[key].health_check()
        elif key in self._embedding_clients:
            embed_client = self._embedding_clients[key]
            health_fn = getattr(embed_client, "health_check", None)
            if health_fn is not None:
                return bool(health_fn())
            return True
        else:
            return False

    def list_providers(self) -> list[dict]:
        """登録されているプロバイダーの一覧を取得する

        Returns:
            プロバイダー情報のリスト
        """
        providers = []
        for key, client in self._clients.items():
            providers.append(
                {
                    "key": key,
                    "type": "llm",
                    "model": client.model,
                    "is_current": key == self._current_llm_key,
                    "available": client.health_check(),
                }
            )
        for key, client in self._embedding_clients.items():
            model_name = getattr(client, "model_name", "unknown")
            health_fn = getattr(client, "health_check", None)
            providers.append(
                {
                    "key": key,
                    "type": "embedding",
                    "model": model_name,
                    "is_current": key == self._current_embedding_key,
                    "available": health_fn() if health_fn else True,
                }
            )
        return providers

    @property
    def current_provider(self) -> str | None:
        """現在選択されているチャットLLMのキーを取得する"""
        return self._current_llm_key

    @property
    def current_embedding(self) -> str | None:
        """現在選択されているembeddingのキーを取得する"""
        return self._current_embedding_key

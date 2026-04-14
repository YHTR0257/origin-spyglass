"""Neo4j PropertyGraphStore 接続管理"""

import os
from collections.abc import Sequence
from typing import Any

from llama_index.core import Document, PropertyGraphIndex
from llama_index.core.llms import LLM  # type: ignore[import-untyped]
from llama_index.core.schema import TransformComponent  # type: ignore[import-untyped]
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore

from spyglass_utils.logging import get_logger

_logger = get_logger(__name__)


class Neo4jGraphStoreManager:
    """Neo4j PropertyGraphStore の接続を管理するクラス

    環境変数から接続情報を取得し、LlamaIndex の Neo4jPropertyGraphStore
    インスタンスを提供します。

    Attributes:
        url: Neo4j Bolt URL
        username: Neo4j ユーザー名
        password: Neo4j パスワード
    """

    def __init__(
        self,
        url: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Neo4jGraphStoreManager を初期化する

        Args:
            url: Neo4j Bolt URL。None の場合は環境変数 DATABASE_URL_BOLT から取得
            username: Neo4j ユーザー名。None の場合は環境変数 NEO4J_USER から取得
            password: Neo4j パスワード。None の場合は環境変数 NEO4J_PASSWORD から取得
        """
        self.url: str = url or os.getenv("DATABASE_URL_BOLT") or "bolt://localhost:7687"
        self.username: str = username or os.getenv("NEO4J_USER") or "neo4j"
        self.password: str = password or os.getenv("NEO4J_PASSWORD") or "password"
        self._store: Neo4jPropertyGraphStore | None = None
        self._index: PropertyGraphIndex | None = None

    @property
    def store(self) -> Neo4jPropertyGraphStore:
        """Neo4jPropertyGraphStore インスタンスを取得する（遅延初期化）

        Returns:
            Neo4jPropertyGraphStore インスタンス
        """
        if self._store is None:
            self._store = Neo4jPropertyGraphStore(
                username=self.username,
                password=self.password,
                url=self.url,
            )
        return self._store

    def query(self, cypher: str, params: dict | None = None) -> list[dict]:
        """Cypher クエリを実行して結果を返す

        Args:
            cypher: 実行する Cypher クエリ
            params: クエリパラメータ

        Returns:
            レコードのリスト（各レコードは dict）
        """
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(self.url, auth=(self.username, self.password))
        try:
            with driver.session() as session:
                result = session.run(cypher, params or {})
                return [record.data() for record in result]
        finally:
            driver.close()

    def create(self, cypher: str, params: dict | None = None) -> list[dict]:
        """CREATE 系 Cypher を実行する。"""
        return self.query(cypher, params)

    def read(self, cypher: str, params: dict | None = None) -> list[dict]:
        """READ 系 Cypher を実行する。"""
        return self.query(cypher, params)

    def update(self, cypher: str, params: dict | None = None) -> list[dict]:
        """UPDATE 系 Cypher を実行する。"""
        return self.query(cypher, params)

    def delete(self, cypher: str, params: dict | None = None) -> list[dict]:
        """DELETE 系 Cypher を実行する。"""
        return self.query(cypher, params)

    def index_documents(
        self,
        documents: Sequence[Document],
        *,
        llm: LLM,
        kg_extractors: list[TransformComponent] | None = None,
        show_progress: bool = False,
    ) -> PropertyGraphIndex:
        """ドキュメント群を index 化し、Neo4j に永続化する。"""
        index = PropertyGraphIndex.from_documents(
            list(documents),
            property_graph_store=self.store,
            llm=llm,
            kg_extractors=kg_extractors,
            show_progress=show_progress,
        )
        self._index = index
        return index

    def get_index(self, *, llm: LLM | None = None) -> PropertyGraphIndex:
        """既存の Neo4j グラフから PropertyGraphIndex を返す（遅延初期化）。"""
        if self._index is None:
            self._index = PropertyGraphIndex.from_existing(
                property_graph_store=self.store,
                llm=llm,
            )
        return self._index

    def retrieval_with_text(
        self,
        query_text: str,
        *,
        llm: LLM,
        max_results: int = 10,
        sub_retrievers: list[str] | None = None,
    ) -> Any:
        """include_text=True でグラフ検索を実行する。"""
        index = self.get_index(llm=llm)
        query_engine = index.as_query_engine(
            include_text=True,
            similarity_top_k=max_results,
            sub_retrievers=sub_retrievers or ["vector", "synonym"],
            llm=llm,
        )
        return query_engine.query(query_text)

    def health_check(self) -> bool:
        """Neo4j サーバーへの接続を確認する

        Returns:
            接続が正常な場合は True、そうでない場合は False
        """
        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(self.url, auth=(self.username, self.password))
            driver.verify_connectivity()
            driver.close()
            return True
        except Exception as e:
            _logger.error(f"Health check failed: {e}")
            return False


class PropertyGraphStore:
    """Neo4j PropertyGraphStore をバックエンドとした PropertyGraphIndex を管理するクラス

    LlamaIndex の PropertyGraphIndex を Neo4j に永続化します。

    Attributes:
        _manager: Neo4j 接続マネージャー
        _graph_store: Neo4jPropertyGraphStore インスタンス
    """

    def __init__(self, manager: Neo4jGraphStoreManager) -> None:
        """PropertyGraphStore を初期化する

        Args:
            manager: Neo4jGraphStoreManager インスタンス
        """
        self._manager = manager

    @property
    def graph_store(self) -> Neo4jPropertyGraphStore:
        """Neo4jPropertyGraphStore インスタンスを返す

        Returns:
            Neo4jPropertyGraphStore インスタンス
        """
        return self._manager.store

    def get_index(self) -> PropertyGraphIndex:
        """既存の Neo4j グラフから PropertyGraphIndex を取得する

        Neo4j に保存済みのグラフデータから検索可能な
        PropertyGraphIndex を構築して返します。

        Returns:
            PropertyGraphIndex インスタンス
        """
        return self._manager.get_index()

    def save(self, index: PropertyGraphIndex) -> None:
        """PropertyGraphIndex の内容を Neo4j に永続化する

        LlamaIndex の PropertyGraphIndex は from_documents() 時点で
        Neo4jPropertyGraphStore に自動書き込みされますが、
        明示的な flush が必要な場合にこのメソッドを使用します。

        Args:
            index: 永続化する PropertyGraphIndex
        """
        index.storage_context.persist()

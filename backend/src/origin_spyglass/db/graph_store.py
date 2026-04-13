"""Neo4j PropertyGraphStore 接続管理"""

import os

from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore

from utils.logging import get_logger

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
        self.url = url or os.getenv("DATABASE_URL_BOLT", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self._store: Neo4jPropertyGraphStore | None = None

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

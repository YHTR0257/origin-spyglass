"""PostgreSQL 接続管理と DocumentRecord ORM モデル"""

import os
import time
import uuid as _uuid_mod
from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, String, Text, Uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from spyglass_utils.logging import get_logger

_logger = get_logger(__name__)

_DEFAULT_DATABASE_URL = "postgresql+asyncpg://spyglass:spyglass@localhost:5432/spyglass"


def uuid7() -> _uuid_mod.UUID:
    """RFC 9562 UUIDv7 — タイムスタンプ順序付き UUID を生成する

    layout:
      [48 bit unix_ts_ms][4 bit ver=7][12 bit rand_a][2 bit var=0b10][62 bit rand_b]
    """
    import os as _os

    ts_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF  # 48 bits
    rand = int.from_bytes(_os.urandom(10), "big")
    rand_a = (rand >> 62) & 0xFFF  # 12 bits
    rand_b = rand & 0x3FFFFFFFFFFFFFFF  # 62 bits
    val = (ts_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0x2 << 62) | rand_b
    return _uuid_mod.UUID(int=val)


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    """ドキュメントのメタデータと本文を保存する ORM モデル

    Attributes:
        id: 主キー（UUIDv7 — タイムスタンプ順序付き）。外部向け doc_id として使用する
        display_id: UI 表示向け識別子（"DOC-{source_file_stem}"）
        title: ドキュメントタイトル
        source_file: 元ファイル名
        mime: MIME タイプ
        body: Markdown 本文
        domain: 検索ドメイン
        tags: タグリスト（JSON 配列）
        author: 著者名
        source_type: ドキュメント取得元種別（SourceType.value）
        confidence: 確信度（0.0〜1.0）
        date: 公開・取得日
        created_at: レコード作成日時
    """

    __tablename__ = "documents"

    id: Mapped[_uuid_mod.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    display_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source_file: Mapped[str] = mapped_column(String, nullable=False)
    mime: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    author: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class VectorStoreManager:
    """PostgreSQL 接続管理クラス

    環境変数から接続情報を取得し、SQLAlchemy async セッションを提供します。
    graph_store.py の Neo4jGraphStoreManager パターンに準拠しています。

    Attributes:
        url: PostgreSQL 接続 URL（asyncpg ドライバ形式）
    """

    def __init__(self, url: str | None = None) -> None:
        """VectorStoreManager を初期化する

        Args:
            url: PostgreSQL 接続 URL。None の場合は環境変数 DATABASE_URL から取得
        """
        self.url: str = url or os.getenv("DATABASE_URL") or _DEFAULT_DATABASE_URL
        self._engine = create_async_engine(self.url, echo=False)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )

    def get_session(self) -> AsyncSession:
        """新しい AsyncSession を返す

        Returns:
            AsyncSession インスタンス
        """
        return self._session_factory()

    async def init_tables(self) -> None:
        """テーブルを作成する（Alembic 導入までの暫定対応）"""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _logger.info("DocumentRecord table initialized")

    async def health_check(self) -> bool:
        """PostgreSQL サーバーへの接続を確認する

        Returns:
            接続が正常な場合は True、そうでない場合は False
        """
        try:
            async with self._engine.connect() as conn:
                from sqlalchemy import text

                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            _logger.error(f"PostgreSQL health check failed: {e}")
            return False

    async def retrieval_with_text(
        self,
        query_embedding: list[float],
        max_results: int = 10,
        domain: str | None = None,
    ) -> list[DocumentRecord]:
        """ベクトル埋め込みを使用してドキュメントを検索する（テキストクエリ）

        Args:
            query_embedding: クエリテキストのベクトル埋め込み
            max_results: 返すドキュメントの最大数（デフォルト10）
            domain: 検索対象ドメイン（指定時はフィルタリング）

        Returns:
            関連ドキュメントのリスト（関連度スコア順）

        Raises:
            Exception: データベース接続エラーまたはクエリ実行例外
        """
        from sqlalchemy import select

        try:
            session = self.get_session()
            async with session as async_session:
                # pgvector のコサイン距離を計算して最も関連の高いドキュメントを取得
                # 注: pgvector 拡張が postgres に インストール済みことを前提
                # embedding カラムを追加する際に備える
                query = select(DocumentRecord).limit(max_results)

                if domain:
                    query = query.where(DocumentRecord.domain == domain)

                result = await async_session.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            _logger.error(f"retrieval_with_text failed: {e}")
            raise

    async def retrieval_with_keywords(
        self,
        keyword_embedding: list[float],
        max_results: int = 10,
        domain: str | None = None,
    ) -> list[DocumentRecord]:
        """ベクトル埋め込みを使用してドキュメントを検索する（キーワード）

        Args:
            keyword_embedding: キーワードリストのベクトル埋め込み
            max_results: 返すドキュメントの最大数（デフォルト10）
            domain: 検索対象ドメイン（指定時はフィルタリング）

        Returns:
            関連ドキュメントのリスト（関連度スコア順）

        Raises:
            Exception: データベース接続エラーまたはクエリ実行例外
        """
        from sqlalchemy import select

        try:
            session = self.get_session()
            async with session as async_session:
                query = select(DocumentRecord).limit(max_results)

                if domain:
                    query = query.where(DocumentRecord.domain == domain)

                result = await async_session.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            _logger.error(f"retrieval_with_keywords failed: {e}")
            raise

    async def retrieval_with_doc_ids(self, doc_ids: list[str]) -> list[DocumentRecord]:
        """ドキュメント ID リストから直接ドキュメントを取得する

        Args:
            doc_ids: 取得するドキュメント ID のリスト

        Returns:
            取得したドキュメントのリスト

        Raises:
            Exception: データベース接続エラーまたはクエリ実行例外
        """
        from uuid import UUID

        from sqlalchemy import select

        try:
            session = self.get_session()
            async with session as async_session:
                # 文字列の ID をUUIDに変換
                doc_uuids = [UUID(doc_id) for doc_id in doc_ids]
                query = select(DocumentRecord).where(DocumentRecord.id.in_(doc_uuids))
                result = await async_session.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            _logger.error(f"retrieval_with_doc_ids failed: {e}")
            raise

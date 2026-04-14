"""infra/vector_store.py のユニットテスト

実際の PostgreSQL は使用せず、SQLite in-memory で ORM とマネージャーを検証する。
"""

import time
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from origin_spyglass.infra.vector_store import Base, DocumentRecord, VectorStoreManager, uuid7

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_SESSION_FACTORY = async_sessionmaker(_ENGINE, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
async def _setup_db() -> AsyncGenerator[None, None]:
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# uuid7
# ---------------------------------------------------------------------------


def test_uuid7_returns_uuid() -> None:
    """uuid7() が uuid.UUID を返す"""
    result = uuid7()
    assert isinstance(result, uuid.UUID)


def test_uuid7_version_is_7() -> None:
    """uuid7() が生成する UUID のバージョンが 7 である"""
    result = uuid7()
    assert result.version == 7


def test_uuid7_is_unique() -> None:
    """uuid7() を複数回呼び出した結果が一意である"""
    ids = {uuid7() for _ in range(100)}
    assert len(ids) == 100


def test_uuid7_is_time_ordered() -> None:
    """uuid7() が時刻順に単調増加する"""
    before = uuid7()
    time.sleep(0.002)  # 2ms 待機してタイムスタンプを確実に進める
    after = uuid7()
    assert before.int < after.int


# ---------------------------------------------------------------------------
# DocumentRecord — ORM モデル
# ---------------------------------------------------------------------------


def _make_record(
    title: str = "Test Doc",
    source_file: str = "test.md",
    domain: str = "tech",
) -> DocumentRecord:
    return DocumentRecord(
        id=uuid7(),
        display_id=f"DOC-{source_file.split('.')[0]}",
        title=title,
        source_file=source_file,
        mime="text/markdown",
        body="# Test\n\nBody.",
        domain=domain,
        tags=["tag1", "tag2"],
        author="Alice",
        source_type="local_markdown",
        confidence=0.9,
        date=date(2026, 4, 1),
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_document_record_insert_and_select() -> None:
    """DocumentRecord を INSERT して SELECT できる"""
    record = _make_record()
    async with _SESSION_FACTORY() as session:
        session.add(record)
        await session.commit()

    async with _SESSION_FACTORY() as session:
        result = await session.execute(select(DocumentRecord))
        rows = result.scalars().all()

    assert len(rows) == 1
    assert rows[0].title == "Test Doc"
    assert rows[0].display_id == "DOC-test"
    assert rows[0].tags == ["tag1", "tag2"]


@pytest.mark.asyncio
async def test_document_record_id_is_primary_key() -> None:
    """id が主キーとして機能し、同一 id の INSERT が失敗する"""
    from sqlalchemy.exc import IntegrityError

    record = _make_record()
    async with _SESSION_FACTORY() as session:
        session.add(record)
        await session.commit()

    dup = _make_record(title="Duplicate")
    dup.id = record.id  # 同じ id を使用

    async with _SESSION_FACTORY() as session:
        session.add(dup)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.asyncio
async def test_document_record_confidence_bounds() -> None:
    """confidence が 0.0 と 1.0 の境界値で正常に保存される"""
    r_min = _make_record(title="Min")
    r_min.confidence = 0.0
    r_max = _make_record(title="Max")
    r_max.confidence = 1.0

    async with _SESSION_FACTORY() as session:
        session.add_all([r_min, r_max])
        await session.commit()

    async with _SESSION_FACTORY() as session:
        result = await session.execute(select(DocumentRecord).order_by(DocumentRecord.confidence))
        rows = result.scalars().all()

    assert rows[0].confidence == 0.0
    assert rows[1].confidence == 1.0


# ---------------------------------------------------------------------------
# VectorStoreManager
# ---------------------------------------------------------------------------


def test_vector_store_manager_uses_env_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """DATABASE_URL 環境変数が設定されている場合にそれを使用する"""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@host/db")
    manager = VectorStoreManager()
    assert manager.url == "postgresql+asyncpg://user:pass@host/db"


def test_vector_store_manager_uses_explicit_url() -> None:
    """コンストラクタに明示的な URL を渡した場合、環境変数より優先される"""
    manager = VectorStoreManager(url="postgresql+asyncpg://explicit/db")
    assert manager.url == "postgresql+asyncpg://explicit/db"


def test_vector_store_manager_get_session_returns_async_session() -> None:
    """get_session() が AsyncSession を返す"""
    manager = VectorStoreManager(url="sqlite+aiosqlite:///:memory:")
    session = manager.get_session()
    assert isinstance(session, AsyncSession)


@pytest.mark.asyncio
async def test_vector_store_manager_init_tables() -> None:
    """init_tables() がテーブルを作成する"""
    manager = VectorStoreManager(url="sqlite+aiosqlite:///:memory:")
    await manager.init_tables()

    async with manager.get_session() as session:
        # テーブルが存在すれば SELECT が成功する
        result = await session.execute(select(DocumentRecord))
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_vector_store_manager_health_check_ok() -> None:
    """health_check() が正常な接続で True を返す"""
    manager = VectorStoreManager(url="sqlite+aiosqlite:///:memory:")
    assert await manager.health_check() is True


@pytest.mark.asyncio
async def test_vector_store_manager_health_check_fails_on_bad_url() -> None:
    """health_check() が不正な URL で False を返す"""
    manager = VectorStoreManager(url="postgresql+asyncpg://invalid:5432/nodb")
    assert await manager.health_check() is False

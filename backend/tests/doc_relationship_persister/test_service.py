"""DocRelationshipPersisterService のユニットテスト

実際の PostgreSQL は使用せず、SQLAlchemy の in-memory SQLite で検証する。
"""

import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from origin_spyglass.doc_relationship_persister import (
    DocRelationshipPersisterInput,
    DocRelationshipPersisterService,
    DuplicateDocumentError,
    MetadataValidationError,
)
from origin_spyglass.infra.vector_store import Base
from origin_spyglass.local_doc_loader.types import FrontmatterMeta, LocalDocumentOutput
from origin_spyglass.schemas.doc_relation import SourceType

_ENGINE = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_SESSION_FACTORY = async_sessionmaker(_ENGINE, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    """各テスト前にテーブルを作成し、テスト後に破棄する"""
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _make_input(
    source_file: str = "report.md",
    domain: str = "tech",
    tags: list[str] | None = None,
    title: str = "My Report",
    author: str = "Alice",
    year: int = 2026,
) -> DocRelationshipPersisterInput:
    meta = FrontmatterMeta(
        domain=domain,
        tags=tags or ["ai", "research"],
        title=title,
        created_at="2026-04-14T00:00:00",
        source_file=source_file,
    )
    doc = LocalDocumentOutput(mime="text/markdown", markdown="# My Report\n\nBody text.", meta=meta)
    return DocRelationshipPersisterInput(
        document=doc,
        author=author,
        source_type=SourceType.LOCAL_MARKDOWN,
        confidence=0.9,
        date=date(year, 4, 1),
    )


@pytest.mark.asyncio
async def test_persist_creates_record() -> None:
    """persist() がドキュメントレコードを作成する"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        output = await service.persist(_make_input())

    # doc_id は UUIDv7 文字列
    assert uuid.UUID(output.doc_id)
    assert output.display_id == "DOC-report"
    assert output.title == "My Report"
    assert output.author == "Alice"
    assert output.source_type == SourceType.LOCAL_MARKDOWN
    assert output.confidence == 0.9
    assert output.domain == "tech"
    assert output.tags == ["ai", "research"]


@pytest.mark.asyncio
async def test_persist_doc_id_is_uuidv7() -> None:
    """doc_id が UUIDv7 形式（バージョン 7）であること"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        output = await service.persist(_make_input())

    uid = uuid.UUID(output.doc_id)
    assert uid.version == 7


@pytest.mark.asyncio
async def test_persist_display_id_from_stem() -> None:
    """display_id が source_file のステムから生成される"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        output = await service.persist(_make_input(source_file="path/to/my-paper.pdf"))

    assert output.display_id == "DOC-my-paper"
    assert uuid.UUID(output.doc_id)  # doc_id は有効な UUID


@pytest.mark.asyncio
async def test_persist_raises_on_duplicate_title_and_year() -> None:
    """同一 title + 年のドキュメントを2回 persist すると DuplicateDocumentError が発生する"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        await service.persist(_make_input(title="Unique Title", year=2026))

    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        with pytest.raises(DuplicateDocumentError) as exc:
            await service.persist(_make_input(title="Unique Title", year=2026))

    assert exc.value.title == "Unique Title"
    assert exc.value.year == 2026


@pytest.mark.asyncio
async def test_persist_allows_same_title_different_year() -> None:
    """同一 title でも年が異なれば重複とみなさない"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        await service.persist(_make_input(source_file="a.md", title="Same Title", year=2025))

    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        output = await service.persist(
            _make_input(source_file="b.md", title="Same Title", year=2026)
        )

    assert uuid.UUID(output.doc_id)


@pytest.mark.asyncio
async def test_persist_raises_on_empty_author() -> None:
    """author が空文字の場合に MetadataValidationError が発生する"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        with pytest.raises(MetadataValidationError) as exc:
            await service.persist(_make_input(author=""))

    assert exc.value.field == "author"


@pytest.mark.asyncio
async def test_persist_raises_on_whitespace_author() -> None:
    """author が空白のみの場合に MetadataValidationError が発生する"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        with pytest.raises(MetadataValidationError) as exc:
            await service.persist(_make_input(author="   "))

    assert exc.value.field == "author"


@pytest.mark.asyncio
async def test_persist_raises_on_empty_source_file() -> None:
    """source_file が空文字の場合に MetadataValidationError が発生する"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        with pytest.raises(MetadataValidationError) as exc:
            await service.persist(_make_input(source_file=""))

    assert exc.value.field == "source_file"


@pytest.mark.asyncio
async def test_persist_raises_on_empty_domain() -> None:
    """domain が空文字の場合に MetadataValidationError が発生する"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        with pytest.raises(MetadataValidationError) as exc:
            await service.persist(_make_input(domain=""))

    assert exc.value.field == "domain"


@pytest.mark.asyncio
async def test_list_documents_returns_all() -> None:
    """list_documents() が全件を返す"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        await service.persist(_make_input(source_file="a.md", domain="tech", title="Doc A"))
        await service.persist(
            _make_input(source_file="b.md", domain="science", title="Doc B", year=2025)
        )

    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        docs = await service.list_documents()

    assert len(docs) == 2


@pytest.mark.asyncio
async def test_list_documents_filters_by_domain() -> None:
    """list_documents(domain=...) がドメインでフィルタリングする"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        await service.persist(_make_input(source_file="a.md", domain="tech", title="Doc A"))
        await service.persist(
            _make_input(source_file="b.md", domain="science", title="Doc B", year=2025)
        )

    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        tech_docs = await service.list_documents(domain="tech")
        science_docs = await service.list_documents(domain="science")

    assert len(tech_docs) == 1
    assert tech_docs[0].domain == "tech"
    assert len(science_docs) == 1
    assert science_docs[0].domain == "science"


@pytest.mark.asyncio
async def test_get_document_returns_record() -> None:
    """get_document() が存在するレコードを返す"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        created = await service.persist(_make_input(source_file="myfile.md"))

    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        result = await service.get_document(created.doc_id)

    assert result is not None
    assert result.doc_id == created.doc_id
    assert result.display_id == "DOC-myfile"


@pytest.mark.asyncio
async def test_get_document_returns_none_for_missing() -> None:
    """get_document() が存在しない doc_id に対して None を返す"""
    fake_id = str(uuid.uuid4())
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        result = await service.get_document(fake_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_document_returns_none_for_invalid_uuid() -> None:
    """get_document() が不正な UUID 文字列に対して None を返す"""
    async with _SESSION_FACTORY() as session:
        service = DocRelationshipPersisterService(session)
        result = await service.get_document("not-a-uuid")

    assert result is None

"""ドキュメントメタデータ CRUD エンドポイント"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from origin_spyglass.doc_relationship_persister import (
    DocRelationshipPersisterInput,
    DocRelationshipPersisterOutput,
    DocRelationshipPersisterService,
    DuplicateDocumentError,
    MetadataValidationError,
)
from origin_spyglass.infra.vector_store import VectorStoreManager

router = APIRouter(prefix="/docs", tags=["docs"])

_manager = VectorStoreManager()


async def _get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _manager.get_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(_get_session)]


@router.post("", response_model=DocRelationshipPersisterOutput, status_code=201)
async def persist_document(
    body: DocRelationshipPersisterInput,
    session: SessionDep,
) -> DocRelationshipPersisterOutput:
    """ドキュメントを PostgreSQL に永続化する

    処理フロー: メタデータバリデーション → 重複チェック → UUIDv7 割当 → INSERT
    """
    service = DocRelationshipPersisterService(session)
    try:
        return await service.persist(body)
    except MetadataValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except DuplicateDocumentError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("", response_model=list[DocRelationshipPersisterOutput])
async def list_documents(
    session: SessionDep,
    domain: Annotated[str | None, Query(description="ドメインフィルタ")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocRelationshipPersisterOutput]:
    """ドキュメント一覧を取得する"""
    service = DocRelationshipPersisterService(session)
    return await service.list_documents(domain=domain, limit=limit, offset=offset)


@router.get("/{doc_id}", response_model=DocRelationshipPersisterOutput)
async def get_document(
    doc_id: str,
    session: SessionDep,
) -> DocRelationshipPersisterOutput:
    """doc_id でドキュメントを取得する"""
    service = DocRelationshipPersisterService(session)
    result = await service.get_document(doc_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    return result

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
from origin_spyglass.doc_relationship_persister.types import VectorStoreUnavailable
from origin_spyglass.doc_retriever import (
    DocIdsRetrieverInput,
    DocIdsRetrieverOutput,
    DocKeywordsRetrieverInput,
    DocKeywordsRetrieverOutput,
    DocRetrieverPipeline,
    DocRetrieverValidationError,
    DocTextRetrieverInput,
    DocTextRetrieverOutput,
    QueryFailed,
)
from origin_spyglass.infra.llm.clients import LlmClientManager
from origin_spyglass.infra.vector_store import VectorStoreManager

router = APIRouter(prefix="/docs", tags=["docs"])

_manager = VectorStoreManager()

_llm_manager = LlmClientManager()

# LlmClientManager にデフォルトクライアントを登録
_llm_manager.register(
    provider="openai_api",
    model="gpt-4o-mini",
)


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


# ============================================================================
# Doc Retriever エンドポイント
# ============================================================================


@router.post(
    "/retrieval/text",
    response_model=DocTextRetrieverOutput,
    status_code=200,
)
async def retrieval_with_text(
    body: DocTextRetrieverInput,
) -> DocTextRetrieverOutput:
    """自然言語質問でドキュメントを検索

    STEP1: 入力バリデーション
    STEP2: LLM 意図解析
    STEP3: pgvector セマンティック検索
    STEP4: 結果整形 + LLM サマリー生成
    """
    pipeline = DocRetrieverPipeline(
        vector_store_manager=_manager,
        llm_client=_llm_manager.get_current_client(),
    )

    try:
        return await pipeline.run_text(body)
    except DocRetrieverValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except QueryFailed as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except VectorStoreUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post(
    "/retrieval/keywords",
    response_model=DocKeywordsRetrieverOutput,
    status_code=200,
)
async def retrieval_with_keywords(
    body: DocKeywordsRetrieverInput,
) -> DocKeywordsRetrieverOutput:
    """キーワードリストでドキュメントを検索

    STEP1: 入力バリデーション
    STEP3: pgvector ベクトル検索
    STEP4: 結果整形 + LLM サマリー生成
    """
    pipeline = DocRetrieverPipeline(
        vector_store_manager=_manager,
        llm_client=_llm_manager.get_current_client(),
    )

    try:
        return await pipeline.run_keywords(body)
    except DocRetrieverValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except QueryFailed as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except VectorStoreUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post(
    "/retrieval/doc-ids",
    response_model=DocIdsRetrieverOutput,
    status_code=200,
)
async def retrieval_with_doc_ids(
    body: DocIdsRetrieverInput,
) -> DocIdsRetrieverOutput:
    """ドキュメント ID リストでドキュメントを取得

    STEP1: 入力バリデーション
    STEP3: ID による直接フェッチ
    STEP4: 結果整形 + LLM サマリー生成
    """
    pipeline = DocRetrieverPipeline(
        vector_store_manager=_manager,
        llm_client=_llm_manager.get_current_client(),
    )

    try:
        return await pipeline.run_doc_ids(body)
    except DocRetrieverValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except QueryFailed as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except VectorStoreUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

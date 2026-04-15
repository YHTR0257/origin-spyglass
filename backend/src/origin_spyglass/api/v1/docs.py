"""ドキュメントメタデータ CRUD エンドポイント"""

import time
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from origin_spyglass.doc_relationship_persister import (
    DocRelationshipPersisterInput,
    DocRelationshipPersisterOutput,
    DocRelationshipPersisterService,
    DuplicateDocumentError,
    MetadataValidationError,
)
from origin_spyglass.doc_retriever import (
    DocIdsRetrieverInput,
    DocKeywordsRetrieverInput,
    DocRetrieverPipeline,
    DocRetrieverValidationError,
    DocTextRetrieverInput,
)
from origin_spyglass.doc_retriever.validation import (
    validate_doc_ids,
    validate_keywords,
    validate_text,
)
from origin_spyglass.infra.llm.clients import LlmClientManager
from origin_spyglass.infra.vector_store import VectorStoreManager
from origin_spyglass.schemas.openai import (
    ChatCompletionStreamChoice,
    ChatCompletionStreamChunk,
    ChatCompletionStreamDelta,
)

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


def _get_doc_retrieval_pipeline() -> DocRetrieverPipeline:
    """Doc Retriever パイプラインを組み立てて返す（テスト時は monkeypatch で差し替え）。"""
    return DocRetrieverPipeline(
        vector_store_manager=_manager,
        llm_client=_llm_manager.get_current_client(),
    )


async def _build_sse_response(
    events: AsyncGenerator[tuple[str, str], None],
) -> StreamingResponse:
    """async generator のイベントを OpenAI SSE 形式の StreamingResponse に変換する。"""
    chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    try:
        model_name: str = _llm_manager.get_current_client().model
    except Exception:
        model_name = "unknown"

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for kind, text in events:
                if kind == "reasoning":
                    delta = ChatCompletionStreamDelta(reasoning_content=text)
                else:
                    delta = ChatCompletionStreamDelta(role="assistant", content=text)
                chunk = ChatCompletionStreamChunk(
                    id=chunk_id,
                    created=created,
                    model=model_name,
                    choices=[ChatCompletionStreamChoice(delta=delta)],
                )
                yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
        except Exception as exc:
            error_chunk = ChatCompletionStreamChunk(
                id=chunk_id,
                created=created,
                model=model_name,
                choices=[
                    ChatCompletionStreamChoice(
                        delta=ChatCompletionStreamDelta(content=f"[ERROR] {exc}"),
                        finish_reason="stop",
                    )
                ],
            )
            yield f"data: {error_chunk.model_dump_json(exclude_none=True)}\n\n"
            yield "data: [DONE]\n\n"
            return

        finish_chunk = ChatCompletionStreamChunk(
            id=chunk_id,
            created=created,
            model=model_name,
            choices=[
                ChatCompletionStreamChoice(
                    delta=ChatCompletionStreamDelta(),
                    finish_reason="stop",
                )
            ],
        )
        yield f"data: {finish_chunk.model_dump_json(exclude_none=True)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


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


@router.post("/retrieval/text")
async def retrieval_with_text(
    body: DocTextRetrieverInput,
) -> StreamingResponse:
    """自然言語質問でドキュメントを検索（OpenAI SSE ストリーミング）

    STEP1: 入力バリデーション（ストリーム開始前、422 を返す）
    STEP2: LLM 意図解析（reasoning チャンク）
    STEP3: pgvector セマンティック検索（reasoning チャンク）
    STEP4: 結果整形 + LLM サマリー生成（reasoning + content チャンク）

    Raises:
        422: 入力バリデーション失敗（ストリーム開始前に返却）
    """
    try:
        validated = validate_text(body)
    except DocRetrieverValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    pipeline = _get_doc_retrieval_pipeline()
    return await _build_sse_response(pipeline.stream_text(validated))


@router.post("/retrieval/keywords")
async def retrieval_with_keywords(
    body: DocKeywordsRetrieverInput,
) -> StreamingResponse:
    """キーワードリストでドキュメントを検索（OpenAI SSE ストリーミング）

    STEP1: 入力バリデーション（ストリーム開始前、422 を返す）
    STEP3: pgvector ベクトル検索（reasoning チャンク）
    STEP4: 結果整形 + LLM サマリー生成（reasoning + content チャンク）

    Raises:
        422: 入力バリデーション失敗（ストリーム開始前に返却）
    """
    try:
        validated = validate_keywords(body)
    except DocRetrieverValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    pipeline = _get_doc_retrieval_pipeline()
    return await _build_sse_response(pipeline.stream_keywords(validated))


@router.post("/retrieval/doc-ids")
async def retrieval_with_doc_ids(
    body: DocIdsRetrieverInput,
) -> StreamingResponse:
    """ドキュメント ID リストでドキュメントを取得（OpenAI SSE ストリーミング）

    STEP1: 入力バリデーション（ストリーム開始前、422 を返す）
    STEP3: ID による直接フェッチ（reasoning チャンク）
    STEP4: 結果整形 + LLM サマリー生成（reasoning + content チャンク）

    Raises:
        422: 入力バリデーション失敗（ストリーム開始前に返却）
    """
    try:
        validated = validate_doc_ids(body)
    except DocRetrieverValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    pipeline = _get_doc_retrieval_pipeline()
    return await _build_sse_response(pipeline.stream_doc_ids(validated))

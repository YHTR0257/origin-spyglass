"""IdeaRelation 永続化・検索エンドポイント"""

import asyncio
import queue
import threading
import time
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from origin_spyglass.idea_relation_persister import (
    ExtractionFailed,
    GraphStoreUnavailable,
    IdeaRelationPersisterInput,
    IdeaRelationPersisterOutput,
    IdeaRelationPersisterPipeline,
    IdeaRelationValidationError,
    PersistFailed,
)
from origin_spyglass.idea_relation_retriever import (
    IdeaRelationRetrieverInput,
    IdeaRelationRetrieverPipeline,
    IdeaRelationRetrieverValidationError,
)
from origin_spyglass.idea_relation_retriever.validation import validate as validate_retriever_input
from origin_spyglass.infra.graph_store import Neo4jGraphStoreManager
from origin_spyglass.infra.llm.clients import LlmClientManager
from origin_spyglass.schemas.openai import (
    ChatCompletionStreamChoice,
    ChatCompletionStreamChunk,
    ChatCompletionStreamDelta,
)

router = APIRouter(prefix="/ideas", tags=["ideas"])

_graph_manager = Neo4jGraphStoreManager()
_llm_manager = LlmClientManager()

_STREAM_SENTINEL = object()


def _get_pipeline() -> IdeaRelationPersisterPipeline:
    """永続化パイプラインを組み立てて返す（テスト時は monkeypatch で差し替え）。"""
    return IdeaRelationPersisterPipeline(
        store_manager=_graph_manager,
        llm=_llm_manager.get_llm(),
    )


def _get_retriever_pipeline() -> IdeaRelationRetrieverPipeline:
    """検索パイプラインを組み立てて返す（テスト時は monkeypatch で差し替え）。"""
    return IdeaRelationRetrieverPipeline(
        store_manager=_graph_manager,
        llm=_llm_manager.get_llm(),
    )


async def _iter_stream_events(
    pipeline: IdeaRelationRetrieverPipeline,
    body: IdeaRelationRetrieverInput,
) -> AsyncGenerator[tuple[str, str] | Exception, None]:
    """同期ジェネレーター pipeline.stream() を非同期イテレーターに変換する。

    例外は通常アイテムとして yield し、呼び出し側で判定する。
    """
    event_q: queue.Queue[object] = queue.Queue()

    def _run_in_thread() -> None:
        try:
            for event in pipeline.stream(body):
                event_q.put(event)
        except Exception as exc:
            event_q.put(exc)
        finally:
            event_q.put(_STREAM_SENTINEL)

    threading.Thread(target=_run_in_thread, daemon=True).start()

    loop = asyncio.get_running_loop()
    while True:
        item = await loop.run_in_executor(None, event_q.get)
        if item is _STREAM_SENTINEL:
            return
        yield item  # type: ignore[misc]


@router.post("/relations", response_model=IdeaRelationPersisterOutput, status_code=201)
async def persist_idea_relations(
    body: IdeaRelationPersisterInput,
) -> IdeaRelationPersisterOutput:
    """ドキュメントから知識トリプレットを抽出し Neo4j に永続化する。

    処理フロー: バリデーション → 文書構造化 → LLM 抽出 → Neo4j Upsert → 結果構築

    Raises:
        422: 入力バリデーション失敗
        503: Neo4j 接続不可
        502: LLM 抽出失敗
        500: Neo4j 書き込み失敗
    """
    pipeline = _get_pipeline()
    try:
        return await asyncio.to_thread(pipeline.run, body)
    except IdeaRelationValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GraphStoreUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ExtractionFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except PersistFailed as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/relations/retrieval")
async def retrieve_idea_relations(body: IdeaRelationRetrieverInput) -> StreamingResponse:
    """自然言語の質問から Neo4j グラフを検索し、OpenAI streaming 形式で回答を返す。

    処理フロー: バリデーション → LLM 意図解析 → グラフ検索 → 結果整形

    各 STEP の進捗は reasoning_content チャンクとして逐次 stream される。
    最終回答は content チャンクとして送出される。

    Raises:
        422: 入力バリデーション失敗（streaming 開始前に返却）
    """
    # バリデーションは streaming 開始前に実施し 422 を返せるようにする
    try:
        await asyncio.to_thread(validate_retriever_input, body)
    except IdeaRelationRetrieverValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    pipeline = _get_retriever_pipeline()
    chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    try:
        model_name: str = _llm_manager.get_current_client().model
    except Exception:
        model_name = "unknown"

    async def generate() -> AsyncGenerator[str, None]:
        async for item in _iter_stream_events(pipeline, body):
            if isinstance(item, Exception):
                error_chunk = ChatCompletionStreamChunk(
                    id=chunk_id,
                    created=created,
                    model=model_name,
                    choices=[
                        ChatCompletionStreamChoice(
                            delta=ChatCompletionStreamDelta(content=f"[ERROR] {item}"),
                            finish_reason="stop",
                        )
                    ],
                )
                yield f"data: {error_chunk.model_dump_json(exclude_none=True)}\n\n"
                yield "data: [DONE]\n\n"
                return

            kind, text = item
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

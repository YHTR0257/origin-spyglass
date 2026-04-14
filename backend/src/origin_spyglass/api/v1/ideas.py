"""IdeaRelation 永続化エンドポイント"""

import asyncio

from fastapi import APIRouter, HTTPException

from origin_spyglass.idea_relation_persister import (
    ExtractionFailed,
    GraphStoreUnavailable,
    IdeaRelationPersisterInput,
    IdeaRelationPersisterOutput,
    IdeaRelationPersisterPipeline,
    IdeaRelationValidationError,
    PersistFailed,
)
from origin_spyglass.infra.graph_store import Neo4jGraphStoreManager
from origin_spyglass.infra.llm.clients import LlmClientManager

router = APIRouter(prefix="/ideas", tags=["ideas"])

_graph_manager = Neo4jGraphStoreManager()
_llm_manager = LlmClientManager()


def _get_pipeline() -> IdeaRelationPersisterPipeline:
    """パイプラインを組み立てて返す（テスト時は monkeypatch で差し替え）。"""
    return IdeaRelationPersisterPipeline(
        store_manager=_graph_manager,
        llm=_llm_manager.get_llm(),
    )


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

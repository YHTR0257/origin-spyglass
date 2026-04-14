"""オーケストレーション: STEP1〜5 を順次実行する"""

import time

from llama_index.core.llms import LLM  # type: ignore[import-untyped]

from origin_spyglass.infra.graph_store import Neo4jGraphStoreManager
from spyglass_utils.logging import get_logger

from .express import build_output
from .extractor import extract_triplets
from .persist import persist_to_graph
from .structure import structure_document
from .types import IdeaRelationPersisterInput, IdeaRelationPersisterOutput
from .validation import validate

_logger = get_logger(__name__)


class IdeaRelationPersisterPipeline:
    """STEP1〜5 を順次呼び出すオーケストレーター。

    store_manager と llm はコンストラクタ注入により、テスト時に差し替え可能。
    run() は同期メソッド。FastAPI ルーターからは asyncio.to_thread() 経由で呼び出す。

    Args:
        store_manager: Neo4jGraphStoreManager インスタンス
        llm: LlamaIndex LLM インスタンス
    """

    def __init__(self, store_manager: Neo4jGraphStoreManager, llm: LLM) -> None:
        self._store_manager = store_manager
        self._llm = llm

    def run(self, input: IdeaRelationPersisterInput) -> IdeaRelationPersisterOutput:
        """パイプラインを実行する。

        Steps:
            STEP1: validate()          — IdeaRelationValidationError on failure
            STEP2: structure_document() — TextNode リストを生成
            STEP3: extract_triplets()  — ExtractionFailed on LLM error
            STEP4: persist_to_graph()  — GraphStoreUnavailable / PersistFailed
            STEP5: build_output()      — always succeeds (best-effort counting)

        Returns:
            IdeaRelationPersisterOutput
        """
        start_ns = time.monotonic_ns()
        _logger.info("IdeaRelationPersister: start doc_id=%s", input.doc_id)

        # STEP1
        validated = validate(input)
        _logger.debug("STEP1 validation passed doc_id=%s", input.doc_id)

        # STEP2
        nodes = structure_document(validated)
        _logger.debug("STEP2 structured %d nodes doc_id=%s", len(nodes), input.doc_id)

        # STEP3
        enriched_nodes = extract_triplets(nodes, self._llm, validated)
        _logger.debug("STEP3 extraction complete doc_id=%s", input.doc_id)

        # STEP4
        index = persist_to_graph(enriched_nodes, validated, self._store_manager, self._llm)
        _logger.info("STEP4 persisted to Neo4j doc_id=%s", input.doc_id)

        # STEP5
        output = build_output(input.doc_id, index, start_ns)
        _logger.info(
            "IdeaRelationPersister: done doc_id=%s nodes=%d edges=%d elapsed_ms=%d",
            output.doc_id,
            output.node_count,
            output.edge_count,
            output.elapsed_ms,
        )
        return output

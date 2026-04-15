"""オーケストレーション: STEP1〜4 を順次実行する"""

import time
from collections.abc import Generator

from llama_index.core.llms import LLM  # type: ignore[import-untyped]

from origin_spyglass.infra.graph_store import Neo4jGraphStoreManager
from spyglass_utils.logging import get_logger

from .express import build_retriever_output
from .interpret import interpret_question
from .query_exploration import explore_graph
from .types import IdeaRelationRetrieverInput, IdeaRelationRetrieverOutput
from .validation import validate

_logger = get_logger(__name__)


class IdeaRelationRetrieverPipeline:
    """STEP1〜4 を順次呼び出すオーケストレーター。

    store_manager と llm はコンストラクタ注入により、テスト時に差し替え可能。
    run() は同期メソッド。FastAPI ルーターからは asyncio.to_thread() 経由で呼び出す。

    Args:
        store_manager: Neo4jGraphStoreManager インスタンス
        llm: LlamaIndex LLM インスタンス
    """

    def __init__(self, store_manager: Neo4jGraphStoreManager, llm: LLM) -> None:
        self._store_manager = store_manager
        self._llm = llm

    def run(self, input: IdeaRelationRetrieverInput) -> IdeaRelationRetrieverOutput:
        """パイプラインを実行する。

        Steps:
            STEP1: validate()           — IdeaRelationRetrieverValidationError on failure
            STEP2: interpret_question() — QueryFailed on LLM failure
            STEP3: explore_graph()      — GraphStoreUnavailable / QueryFailed
            STEP4: build_retriever_output() — always succeeds (best-effort node conversion)

        Returns:
            IdeaRelationRetrieverOutput
        """
        start_ns = time.monotonic_ns()
        _logger.info("IdeaRelationRetriever: start question=%r", input.question[:80])

        # STEP1
        validated = validate(input)
        _logger.debug("STEP1 validation passed")

        # STEP2
        interpreted_query = interpret_question(
            validated.question,
            self._llm,
            domain=validated.domain,
        )
        _logger.debug("STEP2 interpreted query=%r", interpreted_query)

        # STEP3
        query_result = explore_graph(
            interpreted_query,
            self._store_manager,
            self._llm,
            validated.max_results,
        )
        _logger.debug("STEP3 graph exploration done")

        # STEP4
        output = build_retriever_output(validated.question, query_result, start_ns)
        _logger.info(
            "IdeaRelationRetriever: done related_ideas=%d elapsed_ms=%d",
            len(output.related_ideas),
            output.elapsed_ms,
        )
        return output

    def stream(self, input: IdeaRelationRetrieverInput) -> Generator[tuple[str, str], None, None]:
        """各 STEP の進捗を (kind, text) タプルとして逐次 yield するジェネレーター。

        kind は "reasoning"（進捗メッセージ）または "content"（最終回答）のいずれか。
        STEP1 バリデーションは呼び出し側で事前に完了していること。

        Raises:
            QueryFailed: STEP2 LLM 失敗時
            GraphStoreUnavailable: STEP3 Neo4j 接続不可時
            QueryFailed: STEP3 クエリ実行失敗時
        """
        start_ns = time.monotonic_ns()
        _logger.info("IdeaRelationRetriever.stream: start question=%r", input.question[:80])

        yield ("reasoning", "STEP1: バリデーション完了")

        interpreted_query = interpret_question(input.question, self._llm, domain=input.domain)
        _logger.debug("STEP2 interpreted query=%r", interpreted_query)
        yield ("reasoning", f"STEP2: 意図解析完了 → {interpreted_query!r}")

        query_result = explore_graph(
            interpreted_query, self._store_manager, self._llm, input.max_results
        )
        n_results = len(getattr(query_result, "source_nodes", []) or [])
        _logger.debug("STEP3 graph exploration done, %d results", n_results)
        yield ("reasoning", f"STEP3: グラフ検索完了 → {n_results} 件の関連ノードを取得")

        output = build_retriever_output(input.question, query_result, start_ns)
        yield ("reasoning", "STEP4: 結果整形完了")
        yield ("content", output.answer)

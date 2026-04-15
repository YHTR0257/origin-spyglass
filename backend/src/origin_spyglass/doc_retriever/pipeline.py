"""パイプラインオーケストレーション"""

import time

from spyglass_utils.logging import get_logger

from ..infra.llm.base import LlamaIndexLlmClient
from ..infra.vector_store import VectorStoreManager
from . import express, interpret, query_retrieve, validation
from .types import (
    DocIdsRetrieverInput,
    DocIdsRetrieverOutput,
    DocKeywordsRetrieverInput,
    DocKeywordsRetrieverOutput,
    DocTextRetrieverInput,
    DocTextRetrieverOutput,
)

_logger = get_logger(__name__)


class DocRetrieverPipeline:
    """Doc Retriever パイプラインのオーケストレーター

    STEP1: 入力バリデーション
    STEP2: LLM 意図解析（text のみ）
    STEP3: VectorStore 探索
    STEP4: 結果整形
    """

    def __init__(
        self,
        vector_store_manager: VectorStoreManager,
        llm_client: LlamaIndexLlmClient,
    ) -> None:
        """パイプラインを初期化する

        Args:
            vector_store_manager: VectorStoreManager インスタンス
            llm_client: LLM クライアント
        """
        self._vector_store = vector_store_manager
        self._llm_client = llm_client

    async def run_text(self, input_data: DocTextRetrieverInput) -> DocTextRetrieverOutput:
        """テキスト質問による検索パイプラインを実行

        Args:
            input_data: 入力スキーマ

        Returns:
            出力スキーマ

        Raises:
            DocRetrieverValidationError: バリデーション失敗
            QueryFailed: LLM 失敗またはクエリ実行失敗
            VectorStoreUnavailable: VectorStore 接続不可
        """
        start_time = time.time()

        try:
            # STEP1: 入力バリデーション
            validated_input = validation.validate_text(input_data)
            _logger.debug("STEP1 (validate_text) passed")

            # STEP2: LLM 意図解析
            interpreted_query = await interpret.interpret(
                question=validated_input.question,
                llm_client=self._llm_client,
            )
            _logger.debug(f"STEP2 (interpret) completed: {interpreted_query}")

            # STEP3: VectorStore 探索
            related_docs = await query_retrieve.explore_by_text(
                question=interpreted_query,
                manager=self._vector_store,
                llm_client=self._llm_client,
                max_results=validated_input.max_results,
                domain=validated_input.domain,
            )
            _logger.debug(f"STEP3 (explore_by_text) completed: {len(related_docs)} docs found")

            # STEP4: 結果整形
            elapsed_ms = int((time.time() - start_time) * 1000)
            output = await express.express_text(
                question=validated_input.question,
                related_docs=related_docs,
                llm_client=self._llm_client,
                elapsed_ms=elapsed_ms,
            )
            _logger.debug("STEP4 (express_text) completed")

            return output

        except Exception as e:
            _logger.error(f"run_text failed: {e}")
            raise

    async def run_keywords(
        self, input_data: DocKeywordsRetrieverInput
    ) -> DocKeywordsRetrieverOutput:
        """キーワード検索パイプラインを実行

        Args:
            input_data: 入力スキーマ

        Returns:
            出力スキーマ

        Raises:
            DocRetrieverValidationError: バリデーション失敗
            QueryFailed: クエリ実行失敗
            VectorStoreUnavailable: VectorStore 接続不可
        """
        start_time = time.time()

        try:
            # STEP1: 入力バリデーション
            validated_input = validation.validate_keywords(input_data)
            _logger.debug("STEP1 (validate_keywords) passed")

            # STEP2 スキップ: キーワード検索では意図解析不要

            # STEP3: VectorStore 探索
            related_docs = await query_retrieve.explore_by_keywords(
                keywords=validated_input.keywords,
                manager=self._vector_store,
                llm_client=self._llm_client,
                max_results=validated_input.max_results,
                domain=validated_input.domain,
            )
            _logger.debug(f"STEP3 (explore_by_keywords) completed: {len(related_docs)} docs found")

            # STEP4: 結果整形
            elapsed_ms = int((time.time() - start_time) * 1000)
            output = await express.express_keywords(
                keywords=validated_input.keywords,
                related_docs=related_docs,
                llm_client=self._llm_client,
                elapsed_ms=elapsed_ms,
            )
            _logger.debug("STEP4 (express_keywords) completed")

            return output

        except Exception as e:
            _logger.error(f"run_keywords failed: {e}")
            raise

    async def run_doc_ids(self, input_data: DocIdsRetrieverInput) -> DocIdsRetrieverOutput:
        """ID 指定検索パイプラインを実行

        Args:
            input_data: 入力スキーマ

        Returns:
            出力スキーマ

        Raises:
            DocRetrieverValidationError: バリデーション失敗
            QueryFailed: クエリ実行失敗
            VectorStoreUnavailable: VectorStore 接続不可
        """
        start_time = time.time()

        try:
            # STEP1: 入力バリデーション
            validated_input = validation.validate_doc_ids(input_data)
            _logger.debug("STEP1 (validate_doc_ids) passed")

            # STEP2 スキップ: ID 検索では意図解析不要

            # STEP3: VectorStore 探索
            related_docs = await query_retrieve.fetch_by_ids(
                doc_ids=validated_input.doc_ids,
                manager=self._vector_store,
            )
            _logger.debug(f"STEP3 (fetch_by_ids) completed: {len(related_docs)} docs fetched")

            # STEP4: 結果整形
            elapsed_ms = int((time.time() - start_time) * 1000)
            output = await express.express_doc_ids(
                doc_ids=validated_input.doc_ids,
                related_docs=related_docs,
                llm_client=self._llm_client,
                elapsed_ms=elapsed_ms,
            )
            _logger.debug("STEP4 (express_doc_ids) completed")

            return output

        except Exception as e:
            _logger.error(f"run_doc_ids failed: {e}")
            raise

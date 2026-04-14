"""STEP5: 結果整形・出力"""

import time

from llama_index.core import PropertyGraphIndex  # type: ignore[import-untyped]

from spyglass_utils.logging import get_logger

from .types import IdeaRelationPersisterOutput

_logger = get_logger(__name__)


def build_output(
    doc_id: str,
    index: PropertyGraphIndex,
    start_time_ns: int,
    warnings: list[str] | None = None,
) -> IdeaRelationPersisterOutput:
    """STEP5: ノード・エッジ数を集計し出力モデルを構築する。

    カウント処理は best-effort。失敗時は warning を追記して 0 を返す。

    Args:
        doc_id: 入力 doc_id
        index: STEP4 で書き込んだ PropertyGraphIndex
        start_time_ns: パイプライン開始時刻（time.monotonic_ns()）
        warnings: 上流から引き継ぐ警告リスト

    Returns:
        IdeaRelationPersisterOutput
    """
    current_warnings: list[str] = list(warnings or [])
    node_count = 0
    edge_count = 0

    try:
        # get_triplets() -> list[tuple[EntityNode, Relation, EntityNode]]
        triplets = index.property_graph_store.get_triplets()
        edge_count = len(triplets)
        unique_nodes: set[str] = set()
        for subj, _rel, obj in triplets:
            # EntityNode.name は LabelledNode の基底クラスには未定義だが実行時は存在する
            unique_nodes.add(getattr(subj, "name", ""))  # type: ignore[union-attr]
            unique_nodes.add(getattr(obj, "name", ""))  # type: ignore[union-attr]
        unique_nodes.discard("")
        node_count = len(unique_nodes)
    except Exception as exc:
        _logger.warning("node/edge count unavailable: %s", exc)
        current_warnings.append("node/edge count unavailable")

    elapsed_ms = (time.monotonic_ns() - start_time_ns) // 1_000_000

    return IdeaRelationPersisterOutput(
        doc_id=doc_id,
        persisted=True,
        node_count=node_count,
        edge_count=edge_count,
        elapsed_ms=elapsed_ms,
        warnings=current_warnings,
    )

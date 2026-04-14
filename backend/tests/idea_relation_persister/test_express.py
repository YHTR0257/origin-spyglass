"""STEP5: 結果整形のテスト

build_output() は PropertyGraphIndex をモックして呼ぶだけなので外部依存なし。
カウント処理は best-effort のため、get_triplets() が失敗しても例外を raise しないことを確認する。
"""

import time
from unittest.mock import MagicMock

from origin_spyglass.idea_relation_persister.express import build_output


def _make_triplets(
    pairs: list[tuple[str, str]],
) -> list[tuple[MagicMock, MagicMock, MagicMock]]:
    """(subject_name, object_name) ペアから (EntityNode, Relation, EntityNode) モックを生成する。

    実装では getattr(node, 'name', '') でノード名を取得するため、
    モックの .name 属性に文字列を設定している。
    """
    result = []
    for subj_name, obj_name in pairs:
        subj = MagicMock()
        subj.name = subj_name
        obj = MagicMock()
        obj.name = obj_name
        result.append((subj, MagicMock(), obj))
    return result


def _make_index(triplets: list) -> MagicMock:  # type: ignore[type-arg]
    """get_triplets() が指定のトリプレットリストを返す PropertyGraphIndex モックを生成する。"""
    index = MagicMock()
    index.property_graph_store.get_triplets.return_value = triplets
    return index


def test_build_output_basic_structure() -> None:
    index = _make_index(_make_triplets([("Alice", "Bob")]))
    start_ns = time.monotonic_ns()
    output = build_output("doc-001", index, start_ns)

    assert output.doc_id == "doc-001"
    assert output.persisted is True
    assert output.elapsed_ms >= 0
    assert output.warnings == []


def test_build_output_counts_edges_and_nodes() -> None:
    # Alice -> Bob, Bob -> Carol: 2 edges, 3 unique nodes
    triplets = _make_triplets([("Alice", "Bob"), ("Bob", "Carol")])
    index = _make_index(triplets)
    output = build_output("doc-001", index, time.monotonic_ns())

    assert output.edge_count == 2
    assert output.node_count == 3


def test_build_output_deduplicates_nodes() -> None:
    # Alice -> Bob, Alice -> Carol: 2 edges, 3 unique nodes（Alice は 1 回だけカウント）
    triplets = _make_triplets([("Alice", "Bob"), ("Alice", "Carol")])
    index = _make_index(triplets)
    output = build_output("doc-001", index, time.monotonic_ns())

    assert output.edge_count == 2
    assert output.node_count == 3


def test_build_output_zero_triplets() -> None:
    # トリプレットがゼロでも persisted=True を返す（書き込み済みのため）
    index = _make_index([])
    output = build_output("doc-001", index, time.monotonic_ns())

    assert output.edge_count == 0
    assert output.node_count == 0
    assert output.persisted is True


def test_build_output_tolerates_get_triplets_failure() -> None:
    # カウント失敗は best-effort: 例外を raise せず warning を追記してゼロを返す
    index = MagicMock()
    index.property_graph_store.get_triplets.side_effect = Exception("store error")
    output = build_output("doc-001", index, time.monotonic_ns())

    assert output.node_count == 0
    assert output.edge_count == 0
    assert any("unavailable" in w for w in output.warnings)


def test_build_output_propagates_upstream_warnings() -> None:
    # パイプライン上流からの警告は warnings リストに引き継がれる
    index = _make_index([])
    output = build_output("doc-001", index, time.monotonic_ns(), warnings=["upstream warning"])

    assert "upstream warning" in output.warnings


def test_build_output_elapsed_ms_is_non_negative() -> None:
    # time.monotonic_ns() の差分から計算するため常に非負になる
    index = _make_index([])
    start_ns = time.monotonic_ns()
    output = build_output("doc-001", index, start_ns)

    assert output.elapsed_ms >= 0

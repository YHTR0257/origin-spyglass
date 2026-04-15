"""テストユーティリティとファクトリ関数"""

from typing import Any

from origin_spyglass.doc_retriever import (
    DocIdsRetrieverInput,
    DocIdsRetrieverOutput,
    DocKeywordsRetrieverInput,
    DocKeywordsRetrieverOutput,
    DocTextRetrieverInput,
    DocTextRetrieverOutput,
    RetrievedDoc,
)


def make_text_input(**overrides: Any) -> DocTextRetrieverInput:
    """テキスト入力テストデータを生成"""
    defaults: dict[str, Any] = {
        "question": "量子コンピュータと古典コンピュータの関係は？",
        "max_results": 10,
        "domain": None,
        "user_id": None,
    }
    defaults.update(overrides)
    return DocTextRetrieverInput(**defaults)


def make_keywords_input(**overrides: Any) -> DocKeywordsRetrieverInput:
    """キーワード入力テストデータを生成"""
    defaults: dict[str, Any] = {
        "keywords": ["量子コンピュータ", "古典コンピュータ"],
        "max_results": 10,
        "domain": None,
        "user_id": None,
    }
    defaults.update(overrides)
    return DocKeywordsRetrieverInput(**defaults)


def make_ids_input(**overrides: Any) -> DocIdsRetrieverInput:
    """ID入力テストデータを生成"""
    defaults: dict[str, Any] = {
        "doc_ids": ["550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"],
        "user_id": None,
    }
    defaults.update(overrides)
    return DocIdsRetrieverInput(**defaults)


def make_retrieved_doc(**overrides: Any) -> RetrievedDoc:
    """RetrievedDoc テストデータを生成"""
    defaults: dict[str, Any] = {
        "node_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "量子コンピュータの基礎",
        "body_snippet": "量子コンピュータは量子力学の原理を利用して計算を行うコンピュータです。",
        "relevance_score": 0.92,
    }
    defaults.update(overrides)
    return RetrievedDoc(**defaults)


def make_text_output(**overrides: Any) -> DocTextRetrieverOutput:
    """テキスト出力テストデータを生成"""
    defaults: dict[str, Any] = {
        "question": "量子コンピュータと古典コンピュータの関係は？",
        "answer": "量子コンピュータは古典コンピュータとは異なる計算原理を持っています。",
        "related_docs": [make_retrieved_doc()],
        "elapsed_ms": 120,
        "warnings": [],
    }
    defaults.update(overrides)
    return DocTextRetrieverOutput(**defaults)


def make_keywords_output(**overrides: Any) -> DocKeywordsRetrieverOutput:
    """キーワード出力テストデータを生成"""
    defaults: dict[str, Any] = {
        "keywords": ["量子コンピュータ", "古典コンピュータ"],
        "answer": "量子コンピュータと古典コンピュータは異なる計算原理を持っています。",
        "related_docs": [make_retrieved_doc()],
        "elapsed_ms": 80,
        "warnings": [],
    }
    defaults.update(overrides)
    return DocKeywordsRetrieverOutput(**defaults)


def make_ids_output(**overrides: Any) -> DocIdsRetrieverOutput:
    """ID出力テストデータを生成"""
    defaults: dict[str, Any] = {
        "doc_ids": ["550e8400-e29b-41d4-a716-446655440000"],
        "answer": "取得されたドキュメントのサマリーです。",
        "related_docs": [make_retrieved_doc()],
        "elapsed_ms": 50,
        "warnings": [],
    }
    defaults.update(overrides)
    return DocIdsRetrieverOutput(**defaults)

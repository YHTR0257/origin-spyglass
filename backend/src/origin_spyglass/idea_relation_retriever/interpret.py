"""STEP2: LLM を使った質問の意図解析（グラフ検索向けクエリ文字列の精製）"""

from llama_index.core.llms import LLM  # type: ignore[import-untyped]

from .types import QueryFailed

_INTERPRET_PROMPT_TEMPLATE = """\
あなたはナレッジグラフ検索のクエリ最適化アシスタントです。
ユーザーの質問を分析し、グラフ検索に適したキーワード列を生成してください。

ルール:
- 重要な概念・エンティティ・キーワードを空白区切りで出力する
- 質問文そのままではなく、検索に有効なキーワードに変換する
- 出力はキーワードのみ。説明文・記号・改行は含めない
{domain_hint}
質問: {question}

検索キーワード:"""


def interpret_question(question: str, llm: LLM, domain: str | None = None) -> str:
    """LLM を使って質問をグラフ検索向けクエリ文字列に精製する。

    Args:
        question: ユーザーの自然言語質問
        llm: LlamaIndex LLM インスタンス
        domain: 検索対象ドメイン（指定時はプロンプトにヒントとして含める）

    Returns:
        str: グラフ検索に適したクエリ文字列

    Raises:
        QueryFailed: LLM 呼び出し失敗時
    """
    domain_hint = f"- ドメイン「{domain}」に関連するキーワードを優先する\n" if domain else ""
    prompt = _INTERPRET_PROMPT_TEMPLATE.format(
        question=question,
        domain_hint=domain_hint,
    )
    try:
        response = llm.complete(prompt)  # type: ignore[attr-defined]
        return response.text.strip()
    except Exception as exc:
        raise QueryFailed(f"LLM intent interpretation failed: {exc}") from exc

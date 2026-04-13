"""Markdown 清書ロジック — ルールベース + チャンク別 LLM 整形"""

import re

from llama_index.core.node_parser import SentenceSplitter

from spyglass_utils.logging import get_logger

from .types import MarkdownCleaningError

_CHUNK_SIZE = 800
_CHUNK_OVERLAP = 80

logger = get_logger(__name__)


class MarkdownCleaner:
    """markitdown 変換後の Markdown を整形するクラス

    2段階の清書を提供する:
    1. ルールベース（常時実行）: ハイフン改行・ページ番号・余分な空行を除去
    2. LLM チャンク整形（llm 指定時のみ）: コンテキスト長制約を回避するため
       800 トークン単位に分割して各チャンクを LLM で整形し再結合する
    """

    def clean(self, markdown: str, llm=None, *, filename: str = "unknown") -> str:
        """Markdown を整形する

        Args:
            markdown: 整形対象の Markdown テキスト（Frontmatter を含んでもよい）
            llm: LlamaIndex LLM インスタンス。None の場合はルールベースのみ実行

        Returns:
            整形済み Markdown テキスト
        """
        try:
            cleaned = self._rule_based(markdown)
            if llm is not None:
                cleaned = self._llm_chunk_clean(cleaned, llm)
            return cleaned
        except MarkdownCleaningError:
            raise
        except Exception as e:
            logger.error(
                "Markdown cleaning failed: filename=%s detail=%s",
                filename,
                str(e),
                exc_info=True,
            )
            raise MarkdownCleaningError(filename=filename, detail=str(e)) from e

    # ------------------------------------------------------------------
    # Rule-based cleaning
    # ------------------------------------------------------------------

    def _rule_based(self, text: str) -> str:
        header, body = _split_frontmatter(text)

        # 1. ハイフン改行を結合: "プログラ-\nミング" → "プログラミング"
        body = re.sub(r"(\w)-\n(\w)", r"\1\2", body)

        # 2. センテンス途中の改行を空白に置換
        #    改行後が Markdown 構造文字（見出し・リスト・引用・表・コード）で
        #    始まらない場合のみ結合する
        body = re.sub(
            r"(?<=[^\n。.!?！？])\n(?![\n#\-\*>|`\d])",
            " ",
            body,
        )

        # 3. ページ番号（単独の数字のみの行）を除去
        body = re.sub(r"^\s*\d{1,4}\s*$", "", body, flags=re.MULTILINE)

        # 4. 過剰な空行を2行に正規化
        body = re.sub(r"\n{3,}", "\n\n", body)

        return (header + body).strip() + "\n"

    # ------------------------------------------------------------------
    # LLM chunk cleaning
    # ------------------------------------------------------------------

    def _llm_chunk_clean(self, text: str, llm) -> str:
        header, body = _split_frontmatter(text)

        splitter = SentenceSplitter(chunk_size=_CHUNK_SIZE, chunk_overlap=_CHUNK_OVERLAP)
        chunks = splitter.split_text(body)
        if not chunks:
            return header + body

        cleaned_chunks = []
        for chunk in chunks:
            prompt = (
                "以下の Markdown テキストを、情報を一切失わずに読みやすく整形してください。\n"
                "- 文章の途切れを修正し、適切な段落分けにしてください\n"
                "- Markdown の構造（見出し・リスト・コードブロック）は保持してください\n"
                "- 内容の追加・削除・要約は禁止です\n"
                "- 整形後のテキストのみを出力してください（説明文は不要です）\n\n"
                f"---\n{chunk}\n---"
            )
            response = llm.complete(prompt)
            response_text = getattr(response, "text", str(response))
            cleaned_chunks.append(response_text.strip())

        return header + "\n\n".join(cleaned_chunks) + "\n"


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Frontmatter を保護して (header, body) に分割する

    Returns:
        (header, body): header は Frontmatter ブロック（末尾の改行含む）、
        body は残りのテキスト。Frontmatter がない場合は ("", text)。
    """
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[: end + 5], text[end + 5 :]
    return "", text

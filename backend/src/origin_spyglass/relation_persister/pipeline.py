"""関係保存パイプライン - Markdown → PropertyGraphIndex"""

import logging
import time

from llama_index.core import Document, PropertyGraphIndex, Settings
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.prompts import PromptTemplate
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore

from origin_spyglass.relation_persister.context_injector import HeadingContextInjector

logger = logging.getLogger(__name__)

# 日本語テキストに対応した抽出プロンプト
# - 日本語の例を与えることで LLM が日本語のままエンティティを出力する
# - Markdown 記号（**, ##, ` 等）をエンティティに含めないよう明示
_JA_KG_TRIPLET_EXTRACT_PROMPT = PromptTemplate(
    "以下のテキストから、最大 {max_knowledge_triplets} 個の知識トリプレットを"
    "（主語, 述語, 目的語）の形式で抽出してください。\n"
    "・エンティティは日本語または英語の単語・フレーズをそのまま使用してください。\n"
    "・Markdown の記号（**, ##, `, --- など）はエンティティに含めないでください。\n"
    "・ストップワード（は、が、を、の 等）は述語以外では使わないでください。\n"
    "---------------------\n"
    "例:\n"
    "テキスト: Python は汎用プログラミング言語であり、"
    "1991年にグイド・ヴァンロッサムが開発しました。\n"
    "トリプレット:\n"
    "(Python, is, プログラミング言語)\n"
    "(Python, 開発者, グイド・ヴァンロッサム)\n"
    "(Python, 開発年, 1991年)\n"
    "テキスト: ファイル命名規則では、snake_case と kebab-case を"
    "組み合わせることで視認性が向上します。\n"
    "トリプレット:\n"
    "(snake_case, 組み合わせ, kebab-case)\n"
    "(ファイル命名規則, 効果, 視認性向上)\n"
    "---------------------\n"
    "テキスト: {text}\n"
    "トリプレット:\n"
)


class RelationArchiverPipeline:
    """Markdown テキストを Neo4j PropertyGraphStore にインデキシングするパイプライン

    LlamaIndex の SimpleLLMPathExtractor を使ってエンティティと関係を抽出し、
    Neo4j PropertyGraphStore に保存します。

    入力: Markdown テキスト（str）
    出力: Neo4j に永続化された PropertyGraphIndex

    Attributes:
        _graph_store: インデックスの保存先 Neo4jPropertyGraphStore
    """

    def __init__(self, graph_store: Neo4jPropertyGraphStore) -> None:
        """RelationArchiverPipeline を初期化する

        Args:
            graph_store: 保存先の Neo4jPropertyGraphStore
        """
        self._graph_store = graph_store

    def run(
        self,
        markdown_text: str,
        metadata: dict | None = None,
        chunk_size: int = 256,
        chunk_overlap: int = 32,
        show_progress: bool = False,
    ) -> PropertyGraphIndex:
        """Markdown テキストからエンティティ・関係を抽出し Neo4j に保存する

        LlamaIndex Settings.llm が事前に設定されている必要があります。

        Args:
            markdown_text: インデキシング対象の Markdown テキスト
            metadata: Document に付与するメタデータ（doc_id, domain, tags 等）
            chunk_size: チャンクサイズ（トークン数）
            chunk_overlap: チャンクオーバーラップ（トークン数）
            show_progress: 進捗表示フラグ

        Returns:
            Neo4j に保存された PropertyGraphIndex
        """
        t0 = time.perf_counter()
        document = Document(text=markdown_text, metadata=metadata or {})
        logger.info(
            "[pipeline] Document created chars=%d metadata_keys=%s",
            len(markdown_text),
            list((metadata or {}).keys()),
        )

        # 3段階チャンキング:
        # 1. MarkdownNodeParser: 見出し構造（#, ##, ###）でセクション分割
        # 2. HeadingContextInjector: 各ノード先頭に見出し階層パンくずを注入
        #    例: [セクション: 親 > 子] ← LLM がセクション間の関係を認識できる
        # 3. SentenceSplitter: セクションがバッチサイズを超える場合にさらに分割
        md_parser = MarkdownNodeParser()
        heading_injector = HeadingContextInjector()
        sentence_splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        kg_extractor = SimpleLLMPathExtractor(
            llm=Settings.llm,
            extract_prompt=_JA_KG_TRIPLET_EXTRACT_PROMPT,
        )
        logger.info(
            "[pipeline] MarkdownNodeParser + HeadingContextInjector"
            " + SentenceSplitter(chunk_size=%d, chunk_overlap=%d) ready (%.2fs)",
            chunk_size,
            chunk_overlap,
            time.perf_counter() - t0,
        )

        logger.info(
            "[pipeline] PropertyGraphIndex.from_documents START — LLM extraction + Neo4j write"
        )
        t1 = time.perf_counter()
        index = PropertyGraphIndex.from_documents(
            documents=[document],
            property_graph_store=self._graph_store,
            kg_extractors=[kg_extractor],
            transformations=[md_parser, heading_injector, sentence_splitter],
            show_progress=show_progress,
        )
        logger.info(
            "[pipeline] PropertyGraphIndex.from_documents DONE elapsed=%.2fs",
            time.perf_counter() - t1,
        )
        logger.info("[pipeline] total elapsed=%.2fs", time.perf_counter() - t0)

        return index

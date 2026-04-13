"""見出しコンテキスト注入コンポーネント

MarkdownNodeParser が生成した各ノードのテキスト先頭に、
header_path メタデータから読み取った見出し階層パンくずを付加します。

これにより SimpleLLMPathExtractor が
「このテキストは〇〇 > △△ の配下にある」というコンテキストを把握し、
セクション間の階層関係をエンティティ・関係として抽出できるようになります。

例:
    元のノードテキスト:
        ## 子セクション1
        内容A

    注入後のテキスト:
        [セクション: 親セクション > 子セクション1]
        ## 子セクション1
        内容A
"""

from llama_index.core.schema import BaseNode, TransformComponent


class HeadingContextInjector(TransformComponent):
    """header_path メタデータから見出し階層をテキスト先頭に注入する変換コンポーネント"""

    def __call__(self, nodes: list[BaseNode], **kwargs) -> list[BaseNode]:
        for node in nodes:
            breadcrumb = self._build_breadcrumb(node)
            if breadcrumb:
                node.text = f"[セクション: {breadcrumb}]\n{node.text}"
        return nodes

    def _build_breadcrumb(self, node: BaseNode) -> str:
        """header_path と現在ノードの見出しからパンくず文字列を生成する

        header_path の例: '/親セクション/子セクション2/'
        ノードテキスト先頭行の例: '### 孫セクション'

        → '親セクション > 子セクション2 > 孫セクション'
        """
        header_path: str = node.metadata.get("header_path", "/")

        # '/親/子/' → ['親', '子']
        ancestors = [p for p in header_path.strip("/").split("/") if p]

        # ノードテキストの先頭行が見出し行なら追加
        first_line = node.text.splitlines()[0] if node.text else ""
        current = first_line.lstrip("#").strip() if first_line.startswith("#") else ""

        # 祖先がいない場合（ルートレベル）はパンくず不要
        if not ancestors:
            return ""

        parts = ancestors + ([current] if current and current not in ancestors else [])
        return " > ".join(parts)

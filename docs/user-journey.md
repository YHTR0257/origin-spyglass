# Overview
- ORIGIN-Spyglassのユーザージャーニーは、情報収集フェーズと情報取得フェーズに分かれる

## Terms

|用語|概要|定義付け|
|:---:|:---:|:---:|
|semantic knowledge|意味ベースの関連付けがなされた単語群。それぞれは意味を持つ小さな節であり、関連性を持つ|`origin_spyglass/schemas/semantic_knowledge.py`|
|doc-relation|関連付けが行われたドキュメント群。引用関係から、edgeとparamを持つ|`origin_spyglass/schemas/doc_relation.py`|

## Gathering knowledge Phase

1. API経由(WebUI/MCP/)で取得したい情報を定義
2. 論文などのliteratureを保管
- Webサーチ
- ローカルフォルダへのファイルアップロード
3. Local Doc Loader/Web Loaderを用いてテキスト化
- Local Doc Loader: ローカルのPDF/Markdown/JSON/HTMLをパース
- Web Loader: Web上で読み込めるHTMLをパース
- API Fetcher: API経由で収集できるJSONをパース
- Visual Ebidenxe Extractor: png,jpegを読み込みテキスト化
4. 既存のknowledge, relation,

## Retrieving knowledge

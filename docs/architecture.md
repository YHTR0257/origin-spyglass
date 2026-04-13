# Overview
- 本プロジェクトにおけるアーキテクチャはsrc構造を元にしFastAPIを土台として構成する
- レイヤーは上から順に、オーケストレーション層 → ノード実行層 → ツール・統合層 → インフラ層で構成する
- セキュリティ、LLM Factory、ロギング、出力フィルタなどは横断関心として各層から利用する

# Layer
origin_spyglassのレイヤー構成
```mermaid
flowchart TD
    subgraph Orchestration ["オーケストレーション層"]
        Spyglass["Spyglass (LangGraph Research Graph)"]
    end

    subgraph NodeLayer ["ノード実行層"]
        subgraph Gatherer ["Gatherer"]
            LocalDocLoader["Local Doc Loader"]
            SemanticRetriever["Semantic Retriever"]
            RelationExplorer["Relation Explorer"]
            APIFetcher["API Fetcher"]
            VisualEvidenceExtractor["Visual Evidence Extractor"]
        end

        subgraph Processor ["Processor"]
            ContentIdentifier["Content Identifier"]
            ContextIntegrator["Context Integrator"]
        end

        subgraph Synthesizer ["Synthesizer"]
            GapNavigator["Gap Navigator"]
        end

        subgraph Critic ["Critic"]
            SpyglassCritic["Spyglass Critic"]
        end

        subgraph Persister ["Persister"]
            DocumentArchiver["Document Archiver"]
            RelationArchiver["Relation Archiver"]
            SemanticKnowledgePersister["Semantic Knowledge Persister"]
        end
    end

    subgraph ToolIntegration ["ツール・統合層"]
        LlamaIndex["LlamaIndex / PGVectorStore"]
        MarkItDown["MarkItDown / PyMuPDF / OCR"]
        CypherClient["Cypher Query Client"]
        VisionLLM["Vision LLM"]
        ArxivClient["arxiv-python / API Client"]
        TemplateEngine["Template Engine"]
        ReliabilityPrompt["Reliability Prompt"]
        Linker["Linker"]
    end

    subgraph Infra ["インフラ層"]
        Neo4J["Neo4J (GraphStore)"]
        Postgres["PostgreSQL (Table + pgvector)"]
        ExternalApi["External APIs (arXiv etc.)"]
    end

    subgraph CrossCutting ["横断層"]
        Security["agents-keel / Prompt Security"]
        Logging["Logging"]
        OutputFilter["Output Filter"]
        RateLimit["Rate Limiter"]
    end

    Spyglass --> Gatherer
    Spyglass --> Processor
    Spyglass --> Synthesizer
    Spyglass --> Critic
    Spyglass --> Persister

    Gatherer --> ToolIntegration
    Processor --> ToolIntegration
    Synthesizer --> ToolIntegration
    Critic --> ToolIntegration
    Persister --> ToolIntegration

    ToolIntegration --> Infra

    Gatherer -.-> Security
    Processor -.-> Security
    Synthesizer -.-> Security
    Critic -.-> Security
    Persister -.-> Security
```

## Node定義

| Node 分類 | Node 名 | 責務と役割 | 主要ツール |
|:---|:---|:---|:---|
| Gatherer (Local) | Local Doc Loader | ローカルの PDF/MD/JSON/HTML をパースしテキスト化。形式別の前処理（OCR等）を行う。 | MarkItDown / PyMuPDF |
| Gatherer (Vector) | Semantic Retriever | Postgres(pgvector) からテーマに関連するセマンティックな断片を検索・取得する。 | LlamaIndex / PGVectorStore |
| Gatherer (Graph) | Relation Explorer | Neo4J から引用関係、共起概念、著者ネットワークを取得する。 | Cypher Query / Neo4J |
| Gatherer (Online) | API Fetcher | arXiv 等の外部 API から最新の論文メタデータやアブストラクトを収集する。 | arxiv-python / API |
| Gatherer (Vision) | Visual Evidence Extractor | 論文内の図表、グラフ、実験画像から情報を抽出。画像内のテキストや数値を構造化データに変換する。 | Vision LLM (GPT-4o/Claude) |
| Processor (ID) | Content Identifier | 取得情報の種類（理論・手法・事実）を識別し、文脈に応じたタグ付けを行う。 | LLM によるタグ付け |
| Processor (Merge) | Context Integrator | ソース別の情報を単一の調査報告（統合 Markdown）として一貫性を持って再構成する。 | テンプレートエンジン / LLM |
| Synthesizer | Gap Navigator | 統合された知識を俯瞰し、未解決問題（ギャップ）を特定。その解決の難易度と意義を評価する。 | Neo4J自然言語探索 |
| Critic | Spyglass Critic | 調査の網羅性、エビデンスの信頼性、ギャップ特定の妥当性を検証。情報の不備やバイアスを指摘する。 | 信頼性評価プロンプト |
| Persister (Doc) | Document Archiver | 読み込まれた各文書を保存。既存のナレッジネットワークとセマンティックに紐付け、リンクを生成する。 | Postgres / Linker |
| Persister (Rel) | Relation Archiver | 文献調査で得られた引用関係や、抽出された概念、それらの関連性をナレッジグラフ（Neo4j）に記録する。 | Neo4J |
| Persister (Res) | Semantic Knowledge Persister | 調査報告とギャップを保存。過去のギャップリストと結びつけ、未解決問題の履歴を更新する。 | Postgres / Neo4J |

## Utilsの役割
- LLM接続(OpenAI API形式)
- ロギング
- 各プロンプトのセキュリティ担保
    - factory関数として定義することで疎結合を実現
    - LangGraph/LlamaIndex のどちらにも直接依存させず、Nodeから抽象化経由で利用する

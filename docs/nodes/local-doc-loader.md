# Local Doc Loader

## Overview

ローカルに保存されたドキュメントを読み込み、Markdown + YAML Frontmatter 形式に変換する Gatherer ノード。
変換済みドキュメントは下流ノード（Document Archiver など）への入力として使用される。

## Responsibilities

- サポート形式のホワイトリスト検証（4 形式のみ受け付ける）
- 各形式に最適な手法での Markdown 変換
- YAML Frontmatter の付与（ドメイン・タグ・ソースファイル名・作成日時）
- ルールベースの Markdown 清書（オプションで LLM による補正も可能）
- 変換失敗時の構造化ログ出力

## Supported Formats

| 形式 | MIME タイプ | 読み込み戦略 | 依存ライブラリ |
|------|------------|------------|--------------|
| PDF  | `application/pdf` | markitdown 経由で Markdown 変換 | markitdown |
| Markdown | `text/markdown` / `text/plain` | バイト読み込み → UTF-8 デコード（変換不要） | — |
| JSON | `application/json` | UTF-8 デコード → コードブロックとして埋め込み | 標準ライブラリ |
| HTML | `text/html` | markitdown 経由で Markdown 変換（タグ除去・本文抽出） | markitdown |

ホワイトリスト外の MIME タイプは即座に拒否する。MIME 判定にはファイルのバイト列を使用し、拡張子のみへの依存を避ける。

> **Note:** JPEG / PNG などの画像形式は Visual Evidence Extractor ノードが担当する。Local Doc Loader のスコープには含まない。

## Error Handling

| 条件 | 例外 | ログ内容 |
|------|------|---------|
| サポート外の MIME タイプ | `ValueError` | filename, 検出された MIME, サポート一覧 |
| Markdown 変換失敗 | `RuntimeError`（元例外チェーン付き） | filename, MIME, 変換ライブラリのエラーメッセージ |
| UTF-8 デコード失敗（MD/JSON） | `RuntimeError`（`UnicodeDecodeError` をラップ） | filename, エンコーディング情報 |

すべての例外は `logging.error` で出力し、スタックトレースを保持する。

## Data Flow

```
File bytes
  → detect_format()         # MIME 判定・ホワイトリスト検証
  → convert_to_markdown()   # 形式別変換
  → add_frontmatter()       # YAML Frontmatter 付与（冪等）
  → rule_based_clean()      # ルールベース清書（常時実行）
  → [llm_chunk_clean()]     # LLM 清書（llm 引数指定時のみ）
  → Markdown with Frontmatter
```

変換は一時ファイルを介して行い、元ファイルパスへの直接アクセスは行わない（サンドボックス境界）。

## Acceptance Criteria

- PDF / Markdown / JSON / HTML の 4 形式を正常に読み込める
- ホワイトリスト外の形式（例: DOCX, XLSX）を拒否し `ValueError` を送出する
- 読み込み・変換失敗時に `filename`, `MIME`, 原因を含むログを `logging.error` で出力する
- 変換処理は外部ネットワークへアクセスしない（オフライン動作）
- Frontmatter 付与は冪等である（既存 Frontmatter がある場合は上書きしない）

## Related Files

| ファイル | 役割 |
|---------|------|
| [converter.py](../../backend/src/origin_spyglass/local_doc_loader/converter.py) | MIME 判定・Markdown 変換・Frontmatter 付与 |
| [cleaner.py](../../backend/src/origin_spyglass/local_doc_loader/cleaner.py) | ルールベースおよび LLM チャンク清書 |
| [types.py](../../backend/src/origin_spyglass/local_doc_loader/types.py) | `FrontmatterMeta` スキーマ定義 |
| [__init__.py](../../backend/src/origin_spyglass/local_doc_loader/__init__.py) | モジュール公開インターフェース |

テストは `backend/tests/` 配下に `local_doc_loader/` ディレクトリを作成して配置する。

## Test Cases

### 正常系

1. **PDF 読み込み** — 有効な PDF バイト列から Markdown + Frontmatter が生成される
2. **Markdown 読み込み** — UTF-8 エンコードされた `.md` ファイルがそのまま取得される
3. **JSON 読み込み** — 有効な JSON がコードブロックとして Markdown に埋め込まれる
4. **HTML 読み込み** — HTML タグが除去され本文テキストが Markdown に変換される
5. **Frontmatter 冪等性** — 既存 Frontmatter を持つ Markdown に再度付与しても変化しない
6. **ルールベース清書** — ハイフン改行の結合・ページ番号除去・余分な空行の正規化が正しく動作する

### 異常系

7. **非対応形式の拒否** — `.docx` や `.xlsx` を渡した場合に `ValueError` が送出される
8. **破損 PDF の変換失敗** — 不正なバイト列で `RuntimeError` が送出され元例外が保持される
9. **無効 UTF-8 の MD/JSON** — 不正エンコードのファイルで `RuntimeError` が送出される
10. **Frontmatter パースの異常** — 不正な YAML を含む Frontmatter で安全にフォールバックする

### 境界条件

11. **空ファイル** — 0 バイトのファイルで適切なエラーまたは空 Markdown が返される
12. **サンドボックス確認** — 変換処理中に外部ネットワーク呼び出しが発生しないことを確認する

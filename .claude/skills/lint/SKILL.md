# /lint — Linter & Formatter スキル

Python (backend) と TypeScript (frontend) に対して linter/formatter を実行する。

## ツール構成

| 対象 | ツール | 用途 |
|------|--------|------|
| Python (backend) | ruff | lint + format |
| TypeScript (frontend) | prettier | format |

## 実行手順

### Step 1: 対象の確認

引数から実行対象を判断する:

- `backend` または `python` → Python のみ
- `frontend` または `ts` または `typescript` → TypeScript のみ
- 引数なし → 両方実行

### Step 2: 実行

#### Python (backend)

```bash
cd backend
uv run ruff check .          # lint チェック（エラー表示）
uv run ruff check --fix .    # lint 自動修正
uv run ruff format .         # フォーマット適用
```

チェックのみ（fix なし）の場合:
```bash
cd backend
uv run ruff check .
uv run ruff format --check .
```

#### TypeScript (frontend)

```bash
cd frontend
npm run format        # prettier --write .（フォーマット適用）
```

チェックのみの場合:
```bash
cd frontend
npm run format:check  # prettier --check .
```

#### 両方まとめて実行（引数なし）

```bash
cd backend && uv run ruff check --fix . && uv run ruff format .
cd frontend && npm run format
```

### Step 3: 結果の報告

実行後、以下を報告する:

- 修正されたファイル一覧
- 残存する lint エラー（自動修正できなかったもの）
- エラーがない場合は「問題なし」と報告

## 禁止事項

- `--unsafe-fixes` オプションの使用（破壊的変更のリスク）
- `git` 操作（commit, push 等）
- 依存パッケージのインストール（`uv add`, `npm install`）

## 設定ファイル

| ファイル | 内容 |
|---------|------|
| `backend/pyproject.toml` | `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]` |
| `frontend/.prettierrc` | prettier 設定（singleQuote: false, tabWidth: 2 等） |

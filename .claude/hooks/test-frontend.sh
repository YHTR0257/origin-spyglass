#!/bin/bash
# Frontend test hook - Docker コンテナ内で Jest テストを実行する
# Triggered by: PostToolUse on Edit|Write
# Runs only when a file inside frontend/ is modified

FILE=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)

[[ "$FILE" == */lakda/frontend/* ]] || exit 0

echo ">>> frontend file changed: $FILE"
echo ">>> running frontend tests in Docker..."
make test-frontend

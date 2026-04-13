#!/bin/bash
# Backend test hook - Docker コンテナ内でユニットテストを実行する
# Triggered by: PostToolUse on Edit|Write
# Runs only when a file inside backend/ is modified

FILE=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)

[[ "$FILE" == */origin-spyglass/backend/* ]] || exit 0

echo ">>> backend file changed: $FILE"
echo ">>> running backend tests in Docker..."
make test-backend

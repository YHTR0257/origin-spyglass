#!/bin/bash
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
echo "【必須】コード修正・ファイル読み込みの前に /explore と /translate を順に実行せよ。現在のブランチ: ${BRANCH:-不明}"
exit 0

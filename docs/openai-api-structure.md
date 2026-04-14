# OpenAI API 形式の使用上の注意 (origin-spyglass)

この文書は、origin-spyglass が提供する OpenAI 互換 API の実装状況と、実装時/連携時の注意点をまとめたものです。

## このドキュメントで補完した不足点

従来の文書に対して、以下の不足点を補完しました。

1. 現行実装で実際に受け付けるリクエスト項目と制約値 (messages 件数、文字数、max_tokens 上限) の明記
2. OpenAI 互換として未対応の機能 (stream、tools、temperature など) と挙動差分の明記
3. エラー形式の実装差分 (OpenAI 形式ではなく FastAPI 標準の detail) の明記
4. レート制限や出力フィルタなど、運用上の失敗要因の明記
5. stream=true 利用時の注意 (現状は SSE ストリーミングを返さない) の明記
6. /v1/models と /v1/chat/completions の model 整合を呼び出し側で担保する必要性の明記

## 提供エンドポイント

1. POST /v1/chat/completions
2. GET /v1/models

## 互換性サマリ

| 項目 | 状態 | 注意点 |
|---|---|---|
| chat completions 非ストリーミング | 対応 | OpenAI 風レスポンスを返す |
| chat completions ストリーミング (stream=true) | 未対応 | 現状は SSE を返さない |
| model 一覧 | 対応 | 1件の model_id を返す |
| OpenAI 形式エラーオブジェクト | 未対応 | FastAPI 標準の detail を返す |
| usage トークン集計 | 未対応 (固定値) | prompt/completion/total は 0 のまま |

## Chat Completions (POST /v1/chat/completions)

### 受け付けるリクエスト

```json
{
  "model": "llm-agent",
  "messages": [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello"}
  ],
  "max_tokens": 512
}
```

### 入力制約 (現行実装)

1. model は必須
2. messages は必須 (1件以上 100件以下)
3. messages[].role は system / user / assistant のみ
4. messages[].content は必須、最大 10000 文字
5. max_tokens は任意、指定する場合は 1 以上 4096 以下
6. 同一 content が 3 回以上連続した場合はループ検知として拒否

上記に違反した場合は 422 (Unprocessable Entity) になります。

### 正常レスポンス (非ストリーミング)

```json
{
  "id": "chatcmpl-unique-id",
  "object": "chat.completion",
  "created": 1712850000,
  "model": "llm-agent",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! This is a stub response."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

### 実装上の重要な注意

1. 現在の回答文はスタブ実装で固定文言
2. usage は実トークン数を反映していない
3. model の存在確認はサーバー側で厳密に行っていない (受け取った model をそのまま返す)

## ストリーミング利用時の注意

OpenAI 互換クライアントで stream=true を使う場合、通常は SSE で次のようなチャンクを期待します。

```text
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1712850000,"model":"llm-agent","choices":[{"index":0,"delta":{"content":"こん"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1712850000,"model":"llm-agent","choices":[{"index":0,"delta":{"content":"にちは"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1712850000,"model":"llm-agent","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

ただし現行実装では stream パラメータを処理しておらず、SSE ではなく通常の JSON 応答になります。
そのため、stream 必須のクライアントでは待ち状態やパースエラーの原因になります。

## Models (GET /v1/models)

```json
{
  "object": "list",
  "data": [
    {
      "id": "your-agent-id",
      "object": "model",
      "created": 1712850000,
      "owned_by": "origin-spyglass"
    }
  ]
}
```

注意:

1. 返却される model は設定値由来の 1 件
2. ここで返す id はクライアント UI のモデル名として表示されることが多い
3. クライアントは /v1/models の id を /v1/chat/completions の model に使うこと

## エラーハンドリング

### 現行実装で返る主なステータス

1. 422: リクエストバリデーションエラー
2. 429: レート制限超過
3. 500: 出力フィルタで応答がブロックされた場合

### エラー形式の注意

OpenAI 互換の error オブジェクトではなく、FastAPI 標準形式 (detail) が返ります。

例: 429

```json
{
  "detail": "rate limit exceeded"
}
```

例: 422

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "model"],
      "msg": "Field required"
    }
  ]
}
```

OpenAI SDK 依存のクライアントで error.message などを前提にしている場合は、アダプタ層で変換してください。

## 実装チェックリスト

OpenAI 互換性を高める場合は、次を優先して実装してください。

1. stream=true の SSE 応答対応 (content-type, chunk 形式, [DONE])
2. OpenAI 形式のエラーオブジェクト統一
3. /v1/models と /v1/chat/completions の model 整合チェック
4. usage の実トークン集計
5. temperature, top_p, tools など主要パラメータ対応

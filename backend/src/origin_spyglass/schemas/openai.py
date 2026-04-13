"""OpenAI 互換 API スキーマ定義"""

import time
import uuid
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: Role
    content: Annotated[str, Field(min_length=1, max_length=10_000)]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: Annotated[list[ChatMessage], Field(min_length=1, max_length=100)]
    max_tokens: Annotated[int, Field(gt=0, le=4096)] | None = None

    @model_validator(mode="after")
    def no_repeated_loop(self) -> "ChatCompletionRequest":
        """同一メッセージが3回以上連続する場合はループとみなして拒否する。"""
        msgs = self.messages
        for i in range(len(msgs) - 2):
            if msgs[i].content == msgs[i + 1].content == msgs[i + 2].content:
                raise ValueError("repeated messages detected (possible loop)")
        return self


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage = Field(default_factory=ChatCompletionUsage)


class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "origin-spyglass"


class ModelList(BaseModel):
    object: str = "list"
    data: list[ModelObject]

import time
import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

_MAX_MESSAGES = 100
_MAX_CONTENT_LENGTH = 10_000


class ModelObject(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "local"


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelObject]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    max_tokens: int = Field(default=2048, gt=0, le=4096)

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        if not v:
            raise ValueError("messages must not be empty")
        if len(v) > _MAX_MESSAGES:
            raise ValueError(f"messages must not exceed {_MAX_MESSAGES}")
        for msg in v:
            if len(msg.content) > _MAX_CONTENT_LENGTH:
                raise ValueError(
                    f"message content must not exceed {_MAX_CONTENT_LENGTH} characters"
                )
        # Loop detection: 3+ consecutive identical messages indicate a prompt loop
        repeat_count = 1
        for i in range(1, len(v)):
            if v[i].role == v[i - 1].role and v[i].content == v[i - 1].content:
                repeat_count += 1
                if repeat_count >= 3:
                    raise ValueError("detected repeated identical messages (possible loop)")
            else:
                repeat_count = 1
        return v


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage = Field(default_factory=ChatCompletionUsage)

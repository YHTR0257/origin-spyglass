from app.schemas.openai import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)
from app.utils.output_filter import check_sensitive, sanitize
from app.utils.rate_limiter import chat_rate_limiter
from fastapi import APIRouter, HTTPException, Request

from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat/completions", response_model=ChatCompletionResponse)
def chat_completions(req: Request, body: ChatCompletionRequest) -> ChatCompletionResponse:
    client_ip = req.client.host if req.client else "unknown"
    if not chat_rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="rate limit exceeded")

    # TODO: integrate LLM here
    raw_content = "Hello! This is a stub response."

    try:
        check_sensitive(raw_content)
    except ValueError as e:
        logger.error("output blocked by filter: %s", e)
        raise HTTPException(status_code=500, detail="response blocked by output filter") from None

    return ChatCompletionResponse(
        model=body.model,
        choices=[
            ChatCompletionChoice(
                message=ChatMessage(role="assistant", content=sanitize(raw_content))
            )
        ],
    )

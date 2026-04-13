from app.schemas.openai import ModelList, ModelObject
from app.utils import get_settings
from fastapi import APIRouter

from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["models"])


@router.get("/models", response_model=ModelList)
def list_models() -> ModelList:
    settings = get_settings()
    logger.debug("models endpoint called", extra={"model_id": settings.model_id})
    return ModelList(data=[ModelObject(id=settings.model_id)])

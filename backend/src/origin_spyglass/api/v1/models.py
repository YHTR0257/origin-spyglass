from fastapi import APIRouter

from origin_spyglass.schemas.openai import ModelList, ModelObject
from spyglass_utils import get_settings
from spyglass_utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["models"])


@router.get("/models", response_model=ModelList)
def list_models() -> ModelList:
    settings = get_settings()
    logger.debug("models endpoint called", extra={"model_id": settings.model_id})
    return ModelList(data=[ModelObject(id=settings.model_id)])

from app.schemas.openai import ModelList, ModelObject
from app.utils import get_settings
from fastapi import APIRouter

router = APIRouter(tags=["models"])


@router.get("/models", response_model=ModelList)
def list_models() -> ModelList:
    settings = get_settings()
    return ModelList(data=[ModelObject(id=settings.model_id)])

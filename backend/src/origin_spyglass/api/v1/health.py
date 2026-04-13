from fastapi import APIRouter

from origin_spyglass.schemas import HealthResponse
from spyglass_utils import get_settings
from spyglass_utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    logger.debug("health endpoint called")
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
    )

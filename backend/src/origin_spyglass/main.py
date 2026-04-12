from fastapi import FastAPI

from origin_spyglass.api import v1_router
from origin_spyglass.security_headers import SecurityHeadersMiddleware
from utils import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    logger.info("creating FastAPI app", extra={"app_name": settings.app_name})
    app = FastAPI(title=settings.app_name)
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(v1_router, prefix="/v1")
    return app


app = create_app()

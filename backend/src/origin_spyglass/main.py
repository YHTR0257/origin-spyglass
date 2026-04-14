from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from origin_spyglass.api import v1_router
from origin_spyglass.infra.vector_store import VectorStoreManager
from origin_spyglass.security_headers import SecurityHeadersMiddleware
from spyglass_utils import get_settings
from spyglass_utils.logging import get_logger

_logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    manager = VectorStoreManager()
    await manager.init_tables()
    _logger.info("PostgreSQL tables initialized")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(v1_router, prefix="/v1")
    return app


app = create_app()

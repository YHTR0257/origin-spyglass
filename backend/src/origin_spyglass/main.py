from fastapi import FastAPI

from origin_spyglass.api import v1_router
from origin_spyglass.security_headers import SecurityHeadersMiddleware
from spyglass_utils import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(v1_router, prefix="/v1")
    return app


app = create_app()

from fastapi import FastAPI

from app.api import v1_router
from app.security_headers import SecurityHeadersMiddleware
from app.utils import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(v1_router, prefix="/v1")
    return app


app = create_app()

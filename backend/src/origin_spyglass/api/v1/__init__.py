from fastapi import APIRouter

from .chat import router as chat_router
from .docs import router as docs_router
from .health import router as health_router
from .models import router as models_router

v1_router = APIRouter()
v1_router.include_router(health_router)
v1_router.include_router(models_router)
v1_router.include_router(chat_router)
v1_router.include_router(docs_router)

__all__ = ["v1_router"]

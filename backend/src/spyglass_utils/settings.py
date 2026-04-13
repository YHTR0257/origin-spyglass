from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from spyglass_utils.logging import get_logger

logger = get_logger(__name__)


class Settings(BaseSettings):
    app_name: str = "origin-spyglass"
    environment: str = "local"
    model_id: str = "llm-agent"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    logger.debug("loading settings")
    return Settings()

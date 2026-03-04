from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """
    Minimal configuration for the Celery worker service.

    Only the settings required by the ML pipeline are declared here.
    All values are read from environment variables or a ``.env`` file
    located in the *working directory* from which the worker is launched.
    """

    # ── Milvus ────────────────────────────────────────────────────────────────
    MILVUS_URI: str

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = WorkerSettings()


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    return settings

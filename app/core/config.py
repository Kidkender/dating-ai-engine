from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

from app.constants.error_constant import ERROR_DB_CONNECTION_FAILED


class Settings(BaseSettings):

    # Database
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None

    # ML Settings
    EMBEDDING_DIM: int = 512
    SIMILARITY_THRESHOLD: float = 0.7

    PROFILES_PER_PHASE: int = 20

    DATING_APP_TIMEOUT: int = 30
    DATING_APP_BASE_URL: str | None = None
    MIN_FACE_CONFIDENCE: float = 0.7
    DATING_APP_API_KEY: str | None = None
    DATING_APP_IMAGE_BASE_URL: str | None = None

    # Paths
    IMAGE_DIR: str = "./data/images"
    MODEL_DIR: str = "./app/ml/models"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("DATABASE_URL")
    def check_database_url(cls, v: str | None) -> str:
        if not v:
            raise ValueError(ERROR_DB_CONNECTION_FAILED)
        return v


settings = Settings()

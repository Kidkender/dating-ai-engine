from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):

    # Database
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None
    
     # ML Settings
    EMBEDDING_DIM: int = 512
    SIMILARITY_THRESHOLD: float = 0.7
    
    PROFILES_PER_PHASE: int = 20
    PREFERENCE_WEIGHTS = {
        'prefer': 3,
        'like': 2,
        'pass': 0
    }
    
    # Paths
    IMAGE_DIR: str = "./data/images"
    MODEL_DIR: str = "./app/ml/models"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    @field_validator("DATABASE_URL")
    def check_database_url(cls, v: str | None) -> str:
        if not v:
            raise ValueError("DATABASE_URL is missing in .env file")
        return v

settings = Settings()
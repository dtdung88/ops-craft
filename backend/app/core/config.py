from pydantic_settings import BaseSettings
from typing import List
from pydantic import ConfigDict
from pathlib import Path
import os

ENV = os.getenv("ENVIRONMENT", "dev")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE_PATH = PROJECT_ROOT / f".env.{ENV}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "OpsCraft"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Common
    CORS_ORIGINS: List[str]
    
    # Database
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    
    SCRIPT_STORAGE_PATH: str
    
    # Redis / Celery Settings
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    model_config = ConfigDict(env_file=ENV_FILE_PATH, case_sensitive=True, extra="ignore")

settings = Settings()

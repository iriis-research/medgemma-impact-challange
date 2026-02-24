"""
Application Configuration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    app_name: str = "ClariCare AI"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nidanmitra"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # JWT Authentication
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # MedGemma Model Configuration (via Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "amsaravi/medgemma-4b-it:q6"
    max_new_tokens: int = 2048
    
    # Vector Database
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    
    # Storage
    storage_bucket: str = "nidanmitra-documents"
    aws_access_key: str = ""
    aws_secret_key: str = ""
    aws_region: str = "us-east-1"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()

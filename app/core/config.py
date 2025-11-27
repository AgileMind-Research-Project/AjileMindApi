"""
Configuration Settings

Loads configuration from environment variables.
"""

import os
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import EmailStr, field_validator


class Settings(BaseSettings):
    # Application
    APP_NAME: str
    APP_VERSION: str
    ENVIRONMENT: str
    DEBUG: bool
    
    # Server
    HOST: str
    PORT: int
    API_PREFIX: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    
    # Password Policy
    PASSWORD_MIN_LENGTH: int
    PASSWORD_REQUIRE_UPPERCASE: bool
    PASSWORD_REQUIRE_LOWERCASE: bool
    PASSWORD_REQUIRE_NUMBERS: bool
    PASSWORD_REQUIRE_SYMBOLS: bool
    DEFAULT_PASSWORD_SUFFIX: str
    
    # Database
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    
    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str
    REDIS_MAX_CONNECTIONS: int
    
    # Email (SMTP)
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_SECURE: bool
    SMTP_USER: str
    SMTP_APP_PASSWORD: str
    SMTP_FROM_EMAIL: EmailStr
    SMTP_FROM_NAME: str
    
    # Email Subjects
    WELCOME_EMAIL_SUBJECT: str
    PASSWORD_RESET_SUBJECT: str
    TENANT_CREATED_SUBJECT: str
    
    # URLs
    PLATFORM_HOME_URL: str
    AGILEMIND_PLATFORM_URL: str
    FRONTEND_URL: str
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]]
    CORS_CREDENTIALS: bool
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool
    RATE_LIMIT_PER_MINUTE: int
    RATE_LIMIT_PER_HOUR: int
    MAX_LOGIN_ATTEMPTS: int
    LOCKOUT_DURATION_MINUTES: int
    
    # Session
    SESSION_TIMEOUT_MINUTES: int
    
    # Audit Logging
    AUDIT_LOGGING_ENABLED: bool = True
    AUDIT_RETENTION_DAYS: int = 90
    
    # ============================================
    # DOCUMENT CHAT / RAG SETTINGS
    # ============================================
    
    # LLM Configuration (Ollama)
    LLM_API_URL: str = "http://localhost:11434"  # Default to local Ollama
    LLM_MODEL_NAME: str = "llama2"  # Can be changed to mistral, codellama, etc.
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000
    
    # Vector Database (ChromaDB)
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"  # Sentence-transformers model
    
    # Document Processing
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = [".pdf"]
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env file


# Create global settings instance
settings = Settings()

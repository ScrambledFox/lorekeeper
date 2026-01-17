"""
Configuration module for LoreKeeper.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with proper typing."""

    DATABASE_URL: str = "postgresql://lorekeeper:lorekeeper_dev_password@localhost:5432/lorekeeper"
    TEST_DATABASE_URL: str = (
        "postgresql+asyncpg://lorekeeper:lorekeeper_dev_password@localhost/lorekeeper_test"
    )
    ENVIRONMENT: str = "development"
    DEBUG: bool = ENVIRONMENT == "development"
    API_TITLE: str = "LoreKeeper"
    API_VERSION: str = "0.1.0"
    API_DESCRIPTION: str = "Lore and knowledge management system for generated worlds"

    # CORS settings
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Database settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = DEBUG

    EMBEDDING_PROVIDER: str = "mock"

    # OpenAI settings
    OPENAI_API_KEY: str = ""
    OPENAI_ORGANIZATION: str = ""
    OPENAI_EMBEDDING_MODEL_ID: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 1536

    # S3/Object Storage settings
    S3_BUCKET_NAME: str = "lorekeeper-assets"
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_ENDPOINT_URL: str = "https://s3.amazonaws.com"
    S3_PRESIGNED_URL_EXPIRY_SECONDS: int = 3600

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


settings: Settings = Settings()

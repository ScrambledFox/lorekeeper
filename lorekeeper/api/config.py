"""
Configuration module for LoreKeeper.
"""

import os


def _get_env_str(name: str, default: str) -> str:
    """Return an environment variable as a string with a safe default."""
    value = os.getenv(name)
    return value if value is not None else default


class Settings:
    """Application settings with proper typing."""

    DATABASE_URL: str = _get_env_str(
        "DATABASE_URL",
        "postgresql://lorekeeper:lorekeeper_dev_password@localhost:5432/lorekeeper",
    )
    ENVIRONMENT: str = _get_env_str("ENVIRONMENT", "development")
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

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


settings: Settings = Settings()

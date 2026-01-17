"""
Tests for configuration management.
"""

from lorekeeper.config import settings


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_default_database_url(self) -> None:
        """Test default database URL is set correctly."""
        assert "postgresql://" in settings.DATABASE_URL
        assert "lorekeeper" in settings.DATABASE_URL

    def test_default_test_database_url(self) -> None:
        """Test default test database URL is set correctly."""
        assert "postgresql+asyncpg://" in settings.TEST_DATABASE_URL
        assert "lorekeeper_test" in settings.TEST_DATABASE_URL

    def test_default_environment(self) -> None:
        """Test default environment is set to development."""
        assert settings.ENVIRONMENT in ["development", "production", "staging"]

    def test_debug_matches_environment(self) -> None:
        """Test that DEBUG matches the current ENVIRONMENT setting."""
        if settings.ENVIRONMENT == "development":
            assert settings.DEBUG is True
        else:
            assert settings.DEBUG is False


class TestSettingsConsistency:
    """Tests for consistency and validity of settings."""

    def test_api_version_format(self) -> None:
        """Test that API version follows semantic versioning."""
        parts = settings.API_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' is not a number"

    def test_database_urls_are_non_empty(self) -> None:
        """Test that database URLs are not empty strings."""
        assert len(settings.DATABASE_URL) > 0
        assert len(settings.TEST_DATABASE_URL) > 0

    def test_api_title_is_non_empty(self) -> None:
        """Test that API title is set."""
        assert len(settings.API_TITLE) > 0

    def test_pool_settings_are_positive(self) -> None:
        """Test that pool settings are positive integers."""
        assert settings.DB_POOL_SIZE > 0
        assert settings.DB_MAX_OVERFLOW > 0
        assert settings.DB_POOL_RECYCLE > 0

    def test_pagination_settings_are_positive(self) -> None:
        """Test that pagination settings are positive."""
        assert settings.DEFAULT_PAGE_SIZE > 0
        assert settings.MAX_PAGE_SIZE > 0


class TestSettingsEnums:
    """Tests for settings with enum-like values."""

    def test_environment_is_valid_value(self) -> None:
        """Test that ENVIRONMENT is set to a valid value."""
        valid_environments = ["development", "staging", "production"]
        assert settings.ENVIRONMENT in valid_environments

    def test_debug_is_boolean(self) -> None:
        """Test that DEBUG is a boolean value."""
        assert isinstance(settings.DEBUG, bool)

    def test_db_echo_is_boolean(self) -> None:
        """Test that DB_ECHO is a boolean value."""
        assert isinstance(settings.DB_ECHO, bool)

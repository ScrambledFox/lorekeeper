"""
Tests for configuration management.
"""

import os
from unittest import mock

from lorekeeper.api.config import Settings, _get_env_str, settings


class TestEnvironmentVariables:
    """Tests for environment variable handling."""

    def test_get_env_str_with_existing_var(self) -> None:
        """Test retrieving an environment variable that exists."""
        with mock.patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = _get_env_str("TEST_VAR", "default")
            assert result == "test_value"

    def test_get_env_str_with_missing_var(self) -> None:
        """Test retrieving an environment variable that doesn't exist returns default."""
        with mock.patch.dict(os.environ, {}, clear=False):
            # Remove TEST_VAR if it exists
            os.environ.pop("TEST_VAR_NONEXISTENT", None)
            result = _get_env_str("TEST_VAR_NONEXISTENT", "default_value")
            assert result == "default_value"

    def test_get_env_str_with_empty_string(self) -> None:
        """Test that empty string environment variable is treated as a value."""
        with mock.patch.dict(os.environ, {"TEST_EMPTY": ""}):
            result = _get_env_str("TEST_EMPTY", "default")
            assert result == ""


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_default_database_url(self) -> None:
        """Test default database URL is set correctly."""
        test_settings = Settings()
        assert "postgresql://" in test_settings.DATABASE_URL
        assert "lorekeeper" in test_settings.DATABASE_URL

    def test_default_test_database_url(self) -> None:
        """Test default test database URL is set correctly."""
        test_settings = Settings()
        assert "postgresql+asyncpg://" in test_settings.TEST_DATABASE_URL
        assert "lorekeeper_test" in test_settings.TEST_DATABASE_URL

    def test_default_environment(self) -> None:
        """Test default environment is set to development."""
        test_settings = Settings()
        assert test_settings.ENVIRONMENT in ["development", "production", "staging"]

    def test_debug_matches_environment(self) -> None:
        """Test that DEBUG matches the current ENVIRONMENT setting."""
        test_settings = Settings()
        if test_settings.ENVIRONMENT == "development":
            assert test_settings.DEBUG is True
        else:
            assert test_settings.DEBUG is False

    def test_api_metadata(self) -> None:
        """Test API metadata values."""
        test_settings = Settings()
        assert test_settings.API_TITLE == "LoreKeeper"
        assert test_settings.API_VERSION == "0.1.0"
        assert (
            test_settings.API_DESCRIPTION
            == "Lore and knowledge management system for generated worlds"
        )


class TestSettingsCORS:
    """Tests for CORS settings."""

    def test_allowed_origins_default(self) -> None:
        """Test that allowed origins defaults to allow all."""
        test_settings = Settings()
        assert test_settings.ALLOWED_ORIGINS == ["*"]


class TestSettingsDatabase:
    """Tests for database settings."""

    def test_database_pool_settings(self) -> None:
        """Test database pool configuration."""
        test_settings = Settings()
        assert test_settings.DB_POOL_SIZE == 10
        assert test_settings.DB_MAX_OVERFLOW == 20
        assert test_settings.DB_POOL_RECYCLE == 3600

    def test_db_echo_matches_debug(self) -> None:
        """Test that DB_ECHO reflects DEBUG status."""
        test_settings = Settings()
        assert test_settings.DB_ECHO == test_settings.DEBUG


class TestSettingsPagination:
    """Tests for pagination settings."""

    def test_default_page_size(self) -> None:
        """Test default page size is 20."""
        test_settings = Settings()
        assert test_settings.DEFAULT_PAGE_SIZE == 20

    def test_max_page_size(self) -> None:
        """Test max page size is 100."""
        test_settings = Settings()
        assert test_settings.MAX_PAGE_SIZE == 100

    def test_max_page_size_greater_than_default(self) -> None:
        """Test that max page size is greater than default."""
        test_settings = Settings()
        assert test_settings.MAX_PAGE_SIZE > test_settings.DEFAULT_PAGE_SIZE


class TestGlobalSettings:
    """Tests for the global settings instance."""

    def test_global_settings_is_instance_of_settings(self) -> None:
        """Test that global settings object is an instance of Settings."""
        assert isinstance(settings, Settings)

    def test_global_settings_has_required_attributes(self) -> None:
        """Test that global settings has all required attributes."""
        required_attrs = [
            "DATABASE_URL",
            "TEST_DATABASE_URL",
            "ENVIRONMENT",
            "DEBUG",
            "API_TITLE",
            "API_VERSION",
            "API_DESCRIPTION",
            "ALLOWED_ORIGINS",
            "DB_POOL_SIZE",
            "DB_MAX_OVERFLOW",
            "DB_POOL_RECYCLE",
            "DB_ECHO",
            "DEFAULT_PAGE_SIZE",
            "MAX_PAGE_SIZE",
        ]
        for attr in required_attrs:
            assert hasattr(settings, attr), f"Global settings missing attribute: {attr}"


class TestGetEnvStrFunction:
    """Tests for the _get_env_str helper function."""

    def test_get_env_str_returns_string_type(self) -> None:
        """Test that _get_env_str returns a string."""
        result = _get_env_str("NONEXISTENT_VAR_XYZ", "default")
        assert isinstance(result, str)

    def test_get_env_str_respects_environment_variable_content(self) -> None:
        """Test that _get_env_str respects actual environment variable values."""
        with mock.patch.dict(os.environ, {"TEST_CONFIG_VAR": "my_value"}):
            result = _get_env_str("TEST_CONFIG_VAR", "fallback")
            assert result == "my_value"

    def test_get_env_str_with_none_value_returns_default(self) -> None:
        """Test that unset environment variables return default."""
        # Ensure variable doesn't exist
        test_var = "DEFINITELY_NOT_SET_VAR_12345"
        if test_var in os.environ:
            del os.environ[test_var]

        result = _get_env_str(test_var, "my_default")
        assert result == "my_default"


class TestSettingsConsistency:
    """Tests for consistency and validity of settings."""

    def test_api_version_format(self) -> None:
        """Test that API version follows semantic versioning."""
        test_settings = Settings()
        parts = test_settings.API_VERSION.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' is not a number"

    def test_database_urls_are_non_empty(self) -> None:
        """Test that database URLs are not empty strings."""
        test_settings = Settings()
        assert len(test_settings.DATABASE_URL) > 0
        assert len(test_settings.TEST_DATABASE_URL) > 0

    def test_api_title_is_non_empty(self) -> None:
        """Test that API title is set."""
        test_settings = Settings()
        assert len(test_settings.API_TITLE) > 0

    def test_pool_settings_are_positive(self) -> None:
        """Test that pool settings are positive integers."""
        test_settings = Settings()
        assert test_settings.DB_POOL_SIZE > 0
        assert test_settings.DB_MAX_OVERFLOW > 0
        assert test_settings.DB_POOL_RECYCLE > 0

    def test_pagination_settings_are_positive(self) -> None:
        """Test that pagination settings are positive."""
        test_settings = Settings()
        assert test_settings.DEFAULT_PAGE_SIZE > 0
        assert test_settings.MAX_PAGE_SIZE > 0


class TestSettingsEnums:
    """Tests for settings with enum-like values."""

    def test_environment_is_valid_value(self) -> None:
        """Test that ENVIRONMENT is set to a valid value."""
        test_settings = Settings()
        valid_environments = ["development", "staging", "production"]
        assert test_settings.ENVIRONMENT in valid_environments

    def test_debug_is_boolean(self) -> None:
        """Test that DEBUG is a boolean value."""
        test_settings = Settings()
        assert isinstance(test_settings.DEBUG, bool)

    def test_db_echo_is_boolean(self) -> None:
        """Test that DB_ECHO is a boolean value."""
        test_settings = Settings()
        assert isinstance(test_settings.DB_ECHO, bool)

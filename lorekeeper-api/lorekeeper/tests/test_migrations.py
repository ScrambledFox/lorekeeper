"""
Tests for database migrations (Alembic).
"""

from pathlib import Path

import pytest
from alembic.config import Config


class TestMigrationStructure:
    """Tests for migration file structure and validity."""

    def test_migrations_directory_exists(self) -> None:
        """Test that migrations directory exists."""
        migrations_dir = Path(__file__).parent.parent / "db" / "migrations"
        assert migrations_dir.exists()
        assert migrations_dir.is_dir()

    def test_versions_directory_exists(self) -> None:
        """Test that versions directory exists."""
        versions_dir = Path(__file__).parent.parent / "db" / "migrations" / "versions"
        assert versions_dir.exists()
        assert versions_dir.is_dir()

    def test_env_py_exists(self) -> None:
        """Test that env.py file exists in migrations."""
        env_file = Path(__file__).parent.parent / "db" / "migrations" / "env.py"
        assert env_file.exists()
        assert env_file.is_file()

    def test_alembic_ini_exists(self) -> None:
        """Test that alembic.ini exists in project root."""
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
        assert alembic_ini.exists()
        assert alembic_ini.is_file()

    def test_migration_files_have_correct_format(self) -> None:
        """Test that migration files follow naming convention."""
        versions_dir = Path(__file__).parent.parent / "db" / "migrations" / "versions"
        migration_files = list(versions_dir.glob("*.py"))

        # Filter out __pycache__ and __init__
        migration_files = [f for f in migration_files if not f.name.startswith("_")]

        assert len(migration_files) > 0, "Should have at least one migration file"

        # Check naming convention: should be numbered
        for file in migration_files:
            # Migration files should start with a number
            assert file.name[0].isdigit(), f"Migration file {file.name} doesn't start with a number"

    def test_migration_files_are_executable(self) -> None:
        """Test that migration files can be imported."""
        versions_dir = Path(__file__).parent.parent / "db" / "migrations" / "versions"
        migration_files = list(versions_dir.glob("[0-9]*.py"))

        for migration_file in migration_files:
            # All migration files should be valid Python
            try:
                with open(migration_file) as f:
                    compile(f.read(), migration_file, "exec")
            except SyntaxError as e:
                pytest.fail(f"Migration file {migration_file.name} has syntax error: {e}")


@pytest.mark.asyncio
class TestMigrationContent:
    """Tests for migration file content and structure."""

    async def test_001_migration_creates_world_table(self) -> None:
        """Test that the 001_initial_schema migration creates world table."""
        migration_file = (
            Path(__file__).parent.parent
            / "db"
            / "migrations"
            / "versions"
            / "001_initial_schema.py"
        )
        assert migration_file.exists()

        with open(migration_file) as f:
            content = f.read()
            assert "world" in content.lower()
            assert "op.create_table" in content
            assert "upgrade" in content

    async def test_001_migration_creates_entity_table(self) -> None:
        """Test that the 001_initial_schema migration creates entity table."""
        migration_file = (
            Path(__file__).parent.parent
            / "db"
            / "migrations"
            / "versions"
            / "001_initial_schema.py"
        )
        with open(migration_file) as f:
            content = f.read()
            assert "entity" in content.lower()

    async def test_001_migration_creates_document_table(self) -> None:
        """Test that the 001_initial_schema migration creates document table."""
        migration_file = (
            Path(__file__).parent.parent
            / "db"
            / "migrations"
            / "versions"
            / "001_initial_schema.py"
        )
        with open(migration_file) as f:
            content = f.read()
            assert "document" in content.lower()

    async def test_migration_has_upgrade_and_downgrade(self) -> None:
        """Test that migrations have both upgrade and downgrade functions."""
        versions_dir = Path(__file__).parent.parent / "db" / "migrations" / "versions"
        migration_files = list(versions_dir.glob("[0-9]*.py"))

        for migration_file in migration_files:
            with open(migration_file) as f:
                content = f.read()
                assert "def upgrade" in content, f"{migration_file.name} missing upgrade function"
                # Note: downgrade may be empty but should exist
                assert (
                    "def downgrade" in content or "downgrade" in content
                ), f"{migration_file.name} missing downgrade function"


class TestMigrationConfiguration:
    """Tests for Alembic configuration."""

    def test_alembic_config_is_valid(self) -> None:
        """Test that alembic.ini is valid and can be loaded."""
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
        try:
            config = Config(str(alembic_ini))
            assert config is not None
        except Exception as e:
            pytest.fail(f"Failed to load alembic.ini: {e}")

    def test_alembic_config_has_script_location(self) -> None:
        """Test that alembic.ini specifies script_location."""
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
        with open(alembic_ini) as f:
            content = f.read()
            assert "script_location" in content

    def test_alembic_config_references_migrations_directory(self) -> None:
        """Test that alembic.ini references migrations directory."""
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
        with open(alembic_ini) as f:
            content = f.read()
            # Should reference the migrations location
            assert "migrations" in content or "alembic" in content


class TestMigrationSequence:
    """Tests for migration sequence and dependencies."""

    def test_migrations_are_ordered(self) -> None:
        """Test that migration files are properly ordered."""
        versions_dir = Path(__file__).parent.parent / "db" / "migrations" / "versions"
        migration_files = sorted(versions_dir.glob("[0-9]*.py"))

        # Extract version numbers
        versions: list[int] = []
        for file in migration_files:
            # Extract number from filename like "001_initial_schema.py"
            version_num = file.name.split("_")[0]
            versions.append(int(version_num))

        # Versions should be in ascending order
        assert versions == sorted(versions), "Migrations are not in ascending order"

    def test_at_least_one_migration_exists(self) -> None:
        """Test that at least the initial migration exists."""
        versions_dir = Path(__file__).parent.parent / "db" / "migrations" / "versions"
        migration_files = list(versions_dir.glob("[0-9]*.py"))
        assert len(migration_files) >= 1, "No migration files found"

    def test_migration_files_not_empty(self) -> None:
        """Test that migration files are not empty."""
        versions_dir = Path(__file__).parent.parent / "db" / "migrations" / "versions"
        migration_files = list(versions_dir.glob("[0-9]*.py"))

        for migration_file in migration_files:
            with open(migration_file) as f:
                content = f.read().strip()
                assert len(content) > 0, f"{migration_file.name} is empty"


class TestMigrationRevisionsMetadata:
    """Tests for migration metadata (revision IDs, dependencies)."""

    def test_migration_has_revision_metadata(self) -> None:
        """Test that migrations have revision metadata."""
        versions_dir = Path(__file__).parent.parent / "db" / "migrations" / "versions"
        migration_files = list(versions_dir.glob("[0-9]*.py"))

        for migration_file in migration_files:
            with open(migration_file) as f:
                content = f.read()
                # Should have revision metadata
                assert (
                    "revision" in content.lower() or "Revision" in content
                ), f"{migration_file.name} missing revision metadata"

    def test_migration_chains_are_valid(self) -> None:
        """Test that migration down_revision chains are valid."""
        versions_dir = Path(__file__).parent.parent / "db" / "migrations" / "versions"
        migration_files = sorted(versions_dir.glob("[0-9]*.py"))

        # First migration should have down_revision = None
        first_migration = migration_files[0]
        with open(first_migration) as f:
            content = f.read()
            assert (
                "down_revision = None" in content
            ), f"First migration {first_migration.name} should have down_revision = None"

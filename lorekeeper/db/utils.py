"""Database utilities."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime for DB defaults."""
    return datetime.now(UTC)

"""Database utilities."""

from datetime import datetime


def utc_now() -> datetime:
    """Return a naive UTC datetime for DB defaults."""
    return datetime.utcnow()

"""Database utilities."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a naive UTC datetime for DB defaults."""
    # datetime.now(UTC) returns an aware datetime in UTC timezone
    # We convert it to naive (removing the tzinfo) since the DB stores it as TIMESTAMP WITHOUT TIMEZONE
    aware_utc = datetime.now(UTC)
    return aware_utc.replace(tzinfo=None)

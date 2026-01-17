from datetime import UTC, datetime


def utc_now() -> datetime:
    aware_utc = datetime.now(UTC)
    return aware_utc.replace(tzinfo=None)

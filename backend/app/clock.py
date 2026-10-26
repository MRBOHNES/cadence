from datetime import UTC, datetime


def get_now() -> datetime:
    """FastAPI dependency for the current time, so tests can pin the clock."""
    return datetime.now(UTC)

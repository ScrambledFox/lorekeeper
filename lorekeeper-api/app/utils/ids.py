from uuid import UUID


def format_uuid(value: UUID) -> str:
    """
    Format UUID to string.

    Args:
        value: UUID to format

    Returns:
        String representation of UUID
    """
    return str(value)


def parse_uuid(value: str) -> UUID:
    """
    Parse string to UUID.

    Args:
        value: String to parse

    Returns:
        Parsed UUID

    Raises:
        ValueError: If value is not a valid UUID
    """
    try:
        return UUID(value)
    except ValueError as e:
        raise ValueError(f"Invalid UUID format: {value}") from e

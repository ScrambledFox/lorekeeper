"""
Utility functions for LoreKeeper.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


class ApiResponse(Generic[T]):
    """Generic API response wrapper with typing."""

    def __init__(self, data: T, success: bool = True, message: str | None = None) -> None:
        """
        Initialize API response.

        Args:
            data: Response data
            success: Whether the request was successful
            message: Optional message
        """
        self.data = data
        self.success = success
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
        }


class PaginationParams:
    """Pagination parameters with typing."""

    def __init__(self, page: int = 1, page_size: int = 20, max_page_size: int = 100) -> None:
        """
        Initialize pagination parameters.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            max_page_size: Maximum allowed items per page
        """
        self.page = max(1, page)
        self.page_size = min(page_size, max_page_size)
        self.skip = (self.page - 1) * self.page_size

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary."""
        return {
            "page": self.page,
            "page_size": self.page_size,
            "skip": self.skip,
        }


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

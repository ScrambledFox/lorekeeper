from fastapi import HTTPException


class BadRequestException(HTTPException):
    """Exception raised for bad requests."""

    def __init__(self, message: str = "Bad request"):
        super().__init__(status_code=400, detail=message)


class NotFoundException(HTTPException):
    """Exception raised when a requested resource is not found."""

    def __init__(
        self, resource: str = "Resource", id: str | None = None, message: str | None = None
    ):
        detail = message or f"{resource} not found"
        if id:
            detail += f": {id}"
        super().__init__(status_code=404, detail=detail)


class ConflictException(HTTPException):
    """Exception raised for conflict errors."""

    def __init__(self, message: str = "Conflict occurred"):
        super().__init__(status_code=409, detail=message)


class InternalServerErrorException(HTTPException):
    """Exception raised for internal server errors."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(status_code=500, detail=message)

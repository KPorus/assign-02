from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "APP_ERROR",
        status_code: int = 400,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or [{"code": code, "detail": message}]
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", *, code: str = "NOT_FOUND") -> None:
        super().__init__(message, code=code, status_code=404)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict", *, code: str = "CONFLICT") -> None:
        super().__init__(message, code=code, status_code=409)


class ValidationAppError(AppException):
    def __init__(self, message: str = "Validation failed", *, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )

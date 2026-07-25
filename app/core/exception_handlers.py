import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.responses import error_response

logger = logging.getLogger(__name__)


def _validation_errors(exc: RequestValidationError) -> list[dict]:
    errors: list[dict] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = ".".join(str(part) for part in loc if part != "body")
        errors.append(
            {
                "code": "VALIDATION_ERROR",
                "detail": err.get("msg", "Invalid value"),
                "field": field or None,
            }
        )
    return errors


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException):
        return error_response(
            message=exc.message,
            status_code=exc.status_code,
            errors=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError):
        return error_response(
            message="Request validation failed",
            status_code=422,
            errors=_validation_errors(exc),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_request: Request, exc: RateLimitExceeded):
        return error_response(
            message="Rate limit exceeded",
            status_code=429,
            errors=[{"code": "RATE_LIMIT_EXCEEDED", "detail": str(exc.detail)}],
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return error_response(
            message=detail,
            status_code=exc.status_code,
            errors=[{"code": "HTTP_ERROR", "detail": detail}],
        )

    @app.exception_handler(HTTPException)
    async def fastapi_http_exception_handler(_request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return error_response(
            message=detail,
            status_code=exc.status_code,
            errors=[{"code": "HTTP_ERROR", "detail": detail}],
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return error_response(
            message="Internal server error",
            status_code=500,
            errors=[{"code": "INTERNAL_ERROR", "detail": "An unexpected error occurred"}],
        )

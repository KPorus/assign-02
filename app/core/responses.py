from contextvars import ContextVar
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.config import get_settings

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    request_id_ctx.set(request_id)


def build_meta() -> dict[str, Any]:
    settings = get_settings()
    meta: dict[str, Any] = {"version": settings.app_version}
    request_id = get_request_id()
    if request_id:
        meta["request_id"] = request_id
    return meta


def success_response(
    data: Any = None,
    *,
    message: str = "OK",
    status_code: int = 200,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "success": True,
                "message": message,
                "data": data,
                "meta": build_meta(),
            }
        ),
    )


def error_response(
    *,
    message: str,
    status_code: int = 400,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "success": False,
                "message": message,
                "errors": errors or [{"code": "ERROR", "detail": message}],
                "meta": build_meta(),
            }
        ),
    )

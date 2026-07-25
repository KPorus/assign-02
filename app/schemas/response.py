from typing import Any, Optional

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    version: str
    request_id: Optional[str] = None


class SuccessEnvelope(BaseModel):
    success: bool = True
    message: str
    data: Any = None
    meta: ResponseMeta


class ErrorDetail(BaseModel):
    code: str
    detail: str
    field: Optional[str] = None


class ErrorEnvelope(BaseModel):
    success: bool = False
    message: str
    errors: list[ErrorDetail] = Field(default_factory=list)
    meta: ResponseMeta

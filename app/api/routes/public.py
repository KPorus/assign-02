from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.rate_limit import limiter

router = APIRouter(prefix="/public", tags=["public"])
settings = get_settings()


@router.get("/info", status_code=status.HTTP_200_OK)
@limiter.limit(settings.rate_limit_default)
async def public_info(request: Request):
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Welcome stranger! This info is public."},
    )

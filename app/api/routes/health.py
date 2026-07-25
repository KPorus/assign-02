from fastapi import APIRouter, Request, status

from app.config import get_settings
from app.core.rate_limit import limiter
from app.core.responses import success_response

router = APIRouter(tags=["health"])

@router.get("/health")
@limiter.limit(get_settings().rate_limit_default)
async def health(request: Request):
    settings = get_settings()
    return success_response(
        data={
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "environment": settings.environment,
        },
        message="Server is running",
        status_code=status.HTTP_200_OK,
    )

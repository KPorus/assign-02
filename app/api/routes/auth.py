from datetime import timedelta

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import get_settings
from app.core.rate_limit import limiter
from app.core.responses import success_response
from app.dependencies import get_user_service
from app.schemas.user import TokenResponse, UserLogin
from app.services.user_service import UserService
from app.utils.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", status_code=status.HTTP_200_OK)
@limiter.limit(settings.rate_limit_write)
async def login(
    request: Request,
    payload: UserLogin,
    service: UserService = Depends(get_user_service),
):
    user = service.authenticate(str(payload.email), payload.password)
    token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    data = TokenResponse(access_token=token)
    return success_response(
        data=data.model_dump(),
        message="Login successful",
        status_code=status.HTTP_200_OK,
    )


@router.post("/token", status_code=status.HTTP_200_OK)
@limiter.limit(settings.rate_limit_write)
async def login_form(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_user_service),
):
    """OAuth2 password form for Swagger Authorize (username = email)."""
    user = service.authenticate(form_data.username, form_data.password)
    token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    # OAuth2PasswordBearer expects raw token fields at top level for the Authorize flow.
    return {"access_token": token, "token_type": "bearer"}

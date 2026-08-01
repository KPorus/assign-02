from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import get_settings
from app.core.rate_limit import limiter
from app.core.responses import success_response
from app.dependencies import get_user_service, oauth2_scheme
from app.schemas.user import TokenResponse, UserLogin
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", status_code=status.HTTP_200_OK)
@limiter.limit(settings.rate_limit_write)
async def login(
    request: Request,
    payload: UserLogin,
    service: UserService = Depends(get_user_service),
):
    result = service.authenticate(str(payload.email), payload.password)
    data = TokenResponse(access_token=result.access_token)
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
    result = service.authenticate(form_data.username, form_data.password)
    return {"access_token": result.access_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_200_OK)
@limiter.limit(settings.rate_limit_write)
async def logout(
    request: Request,
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(get_user_service),
):
    """Sign out and remove the Supabase session for the current access token."""
    service.sign_out(token)
    return success_response(
        data=None,
        message="Signed out successfully",
        status_code=status.HTTP_200_OK,
    )

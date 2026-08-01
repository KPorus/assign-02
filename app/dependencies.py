from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.schemas.user import UserResponse
from app.services.post_service import PostService, post_service
from app.services.user_service import UserService, user_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_post_service() -> PostService:
    return post_service


def get_user_service() -> UserService:
    return user_service


def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    return service.get_by_access_token(token)

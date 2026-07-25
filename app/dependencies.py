from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.exceptions import NotFoundError, UnauthorizedError
from app.schemas.user import UserResponse
from app.services.post_service import PostService, post_service
from app.services.user_service import UserService, user_service
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_post_service() -> PostService:
    return post_service


def get_user_service() -> UserService:
    return user_service


def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    payload = decode_access_token(token)
    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("Invalid token payload")
    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid token subject") from exc
    try:
        return service.get(user_id)
    except NotFoundError as exc:
        raise UnauthorizedError("User not found for token") from exc

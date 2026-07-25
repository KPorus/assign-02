from app.core.exceptions import NotFoundError
from app.db import database as db
from app.schemas.user import UserCreate, UserResponse, UserSearchResult, UserUpdate
from datetime import datetime

from app.utils.security import hash_password


def _to_user(row: dict) -> UserResponse:
    return UserResponse.model_validate(row)

class UserService:
    def create(self, payload: UserCreate) -> UserResponse:
        row = db.insert_user(
            username=payload.username,
            email=payload.email,
            password=hash_password(payload.password),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return _to_user(row)

    def get(self, user_id: int) -> UserResponse:
        row = db.get_user_by_id(user_id)
        if row is None:
            raise NotFoundError(f"User with id {user_id} not found")
        return _to_user(row)

    def update(self, user_id: int, payload: UserUpdate) -> UserResponse:
        row = db.update_user(
            user_id,
            payload.username,
            payload.email,
            payload.password,
            updated_at=datetime.now(),
        )
        if row is None:
            raise NotFoundError(f"User with id {user_id} not found")
        return _to_user(row)

    def delete(self, user_id: int) -> UserResponse:
        row = db.delete_user(user_id)
        if row is None:
            raise NotFoundError(f"User with id {user_id} not found")
        return _to_user(row)

user_service = UserService()
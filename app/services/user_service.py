from datetime import datetime

from psycopg.errors import UniqueViolation

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.db import database as db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.utils.security import hash_password, verify_password


def _to_user(row: dict) -> UserResponse:
    return UserResponse.model_validate(row)


class UserService:
    def create(self, payload: UserCreate) -> UserResponse:
        existing = db.get_user_by_email(str(payload.email))
        if existing is not None:
            raise ConflictError("Email already registered")
        try:
            row = db.insert_user(
                username=payload.username,
                email=str(payload.email),
                password=hash_password(payload.password),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        except UniqueViolation as exc:
            raise ConflictError("Username or email already exists") from exc
        return _to_user(row)

    def get(self, user_id: int) -> UserResponse:
        row = db.get_user_by_id(user_id)
        if row is None:
            raise NotFoundError(f"User with id {user_id} not found")
        return _to_user(row)

    def update(self, user_id: int, payload: UserUpdate) -> UserResponse:
        hashed: str | None = None
        if payload.password is not None:
            hashed = hash_password(payload.password)
        row = db.update_user(
            user_id,
            payload.username,
            str(payload.email) if payload.email is not None else None,
            hashed,
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

    def authenticate(self, email: str, password: str) -> UserResponse:
        row = db.get_user_by_email(email)
        if row is None or not verify_password(password, row["password"]):
            raise UnauthorizedError("Invalid email or password")
        return _to_user(
            {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )


user_service = UserService()

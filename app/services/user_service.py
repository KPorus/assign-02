"""User profiles and Auth via Supabase; posts stay in local Postgres.

Passwords live only in Supabase Auth (auth.users), never in public.users.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, NoReturn

from postgrest.exceptions import APIError
from supabase_auth.errors import AuthApiError
from supabase_auth.types import User as AuthUser

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
    ValidationAppError,
)
from app.db import database as db
from app.db.supabase_client import create_auth_client, get_supabase
from app.schemas.user import AuthResult, UserCreate, UserResponse, UserUpdate

USERS_TABLE = "users"


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _row_to_user(row: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=str(row["id"]),
        username=row["username"],
        email=row["email"],
        created_at=_parse_dt(row.get("created_at")),
        updated_at=_parse_dt(row.get("updated_at")),
    )


def _placeholder_user(user_id: str) -> UserResponse:
    now = datetime.now(timezone.utc)
    return UserResponse(
        id=user_id,
        username="unknown",
        email="unknown@example.com",
        created_at=now,
        updated_at=now,
    )


def _raise_auth_error(exc: AuthApiError) -> NoReturn:
    message = str(exc)
    lower = message.lower()
    if "rate limit" in lower or getattr(exc, "status", None) == 429:
        raise TooManyRequestsError(
            "Supabase Auth rate limit exceeded. Wait a minute, or disable "
            "email confirmation in the Supabase dashboard for local testing."
        ) from exc
    if "already" in lower or "registered" in lower or "exists" in lower:
        raise ConflictError("Email already registered") from exc
    if "not allowed" in lower:
        raise ValidationAppError(
            "Supabase rejected user creation (User not allowed). "
            "Usually the API client was logged in as a normal user, or "
            "Email signup is disabled under Authentication → Providers → Email. "
            "Rebuild/restart the API after the latest fix, then try again."
        ) from exc
    if "invalid" in lower:
        raise ValidationAppError(
            message,
            details=[{"code": "VALIDATION_ERROR", "detail": message, "field": "email"}],
        ) from exc
    raise ValidationAppError(message) from exc


class UserService:
    def _upsert_profile(
        self,
        *,
        user_id: str,
        username: str,
        email: str,
    ) -> UserResponse:
        client = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        profile = {
            "id": user_id,
            "username": username,
            "email": email,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = (
                client.table(USERS_TABLE)
                .upsert(profile, on_conflict="id")
                .execute()
            )
        except APIError as exc:
            if getattr(exc, "code", "") == "23505" or "duplicate" in str(exc).lower():
                raise ConflictError("Username or email already registered") from exc
            raise

        rows = result.data or []
        if rows:
            return _row_to_user(rows[0])

        # Upsert can return empty under RLS; verify with a follow-up read.
        try:
            return self.get(user_id)
        except NotFoundError as exc:
            raise ConflictError(
                "Failed to save user profile in public.users. "
                "Run docs/supabase_users.sql and ensure SUPABASE_KEY is the service_role key."
            ) from exc

    def _ensure_profile_from_auth(self, auth_user: AuthUser) -> UserResponse:
        user_id = str(auth_user.id)
        try:
            return self.get(user_id)
        except NotFoundError:
            meta = auth_user.user_metadata or {}
            username = str(meta.get("username") or (auth_user.email or "user").split("@")[0])
            email = str(auth_user.email or f"{user_id}@users.local")
            return self._upsert_profile(user_id=user_id, username=username, email=email)

    def create(self, payload: UserCreate) -> UserResponse:
        """Create Auth user (password in Auth) + profile row in public.users."""
        client = get_supabase()
        try:
            auth_response = client.auth.admin.create_user(
                {
                    "email": str(payload.email),
                    "password": payload.password,
                    "email_confirm": True,
                    "user_metadata": {"username": payload.username},
                }
            )
        except AuthApiError as exc:
            _raise_auth_error(exc)

        auth_user = auth_response.user
        if auth_user is None:
            raise ConflictError("Unable to create user (check Supabase Auth settings)")

        user_id = str(auth_user.id)
        try:
            return self._upsert_profile(
                user_id=user_id,
                username=payload.username,
                email=str(payload.email),
            )
        except Exception:
            try:
                client.auth.admin.delete_user(user_id)
            except Exception:
                pass
            raise

    def get(self, user_id: str) -> UserResponse:
        client = get_supabase()
        result = (
            client.table(USERS_TABLE)
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            raise NotFoundError(f"User with id {user_id} not found")
        return _row_to_user(rows[0])

    def get_many(self, user_ids: list[str]) -> dict[str, UserResponse]:
        unique = list({uid for uid in user_ids if uid})
        if not unique:
            return {}
        client = get_supabase()
        result = (
            client.table(USERS_TABLE)
            .select("*")
            .in_("id", unique)
            .execute()
        )
        users: dict[str, UserResponse] = {}
        for row in result.data or []:
            user = _row_to_user(row)
            users[user.id] = user
        return users

    def resolve_authors(self, user_ids: list[str]) -> dict[str, UserResponse]:
        found = self.get_many(user_ids)
        return {
            uid: found.get(uid) or _placeholder_user(uid)
            for uid in {u for u in user_ids if u}
        }

    def update(self, user_id: str, payload: UserUpdate) -> UserResponse:
        client = get_supabase()
        existing = self.get(user_id)

        auth_updates: dict[str, Any] = {}
        if payload.email is not None:
            auth_updates["email"] = str(payload.email)
        if payload.password is not None:
            auth_updates["password"] = payload.password
        if auth_updates:
            try:
                client.auth.admin.update_user_by_id(user_id, auth_updates)
            except AuthApiError as exc:
                _raise_auth_error(exc)

        profile_updates: dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if payload.username is not None:
            profile_updates["username"] = payload.username
        if payload.email is not None:
            profile_updates["email"] = str(payload.email)

        try:
            result = (
                client.table(USERS_TABLE)
                .update(profile_updates)
                .eq("id", user_id)
                .execute()
            )
        except APIError as exc:
            if getattr(exc, "code", "") == "23505" or "duplicate" in str(exc).lower():
                raise ConflictError("Username or email already registered") from exc
            raise

        rows = result.data or []
        if not rows:
            return UserResponse(
                id=existing.id,
                username=payload.username or existing.username,
                email=payload.email or existing.email,
                created_at=existing.created_at,
                updated_at=datetime.now(timezone.utc),
            )
        return _row_to_user(rows[0])

    def delete(self, user_id: str) -> UserResponse:
        user = self.get(user_id)
        client = get_supabase()
        db.delete_posts_by_user_id(user_id)
        try:
            client.auth.admin.delete_user(user_id)
        except AuthApiError as exc:
            raise NotFoundError(f"User with id {user_id} not found") from exc
        try:
            client.table(USERS_TABLE).delete().eq("id", user_id).execute()
        except APIError:
            pass
        return user

    def authenticate(self, email: str, password: str) -> AuthResult:
        # Use a throwaway client so sign-in does not pollute the admin client.
        auth_client = create_auth_client()
        try:
            auth_response = auth_client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except AuthApiError as exc:
            raise UnauthorizedError("Invalid email or password") from exc

        session = auth_response.session
        auth_user = auth_response.user
        if session is None or auth_user is None or not session.access_token:
            raise UnauthorizedError("Invalid email or password")

        # Heal orphan Auth users that never got a public.users row.
        user = self._ensure_profile_from_auth(auth_user)
        return AuthResult(user=user, access_token=session.access_token)

    def get_by_access_token(self, token: str) -> UserResponse:
        auth_client = create_auth_client()
        try:
            response = auth_client.auth.get_user(token)
        except AuthApiError as exc:
            raise UnauthorizedError("Invalid or expired token") from exc
        auth_user = response.user
        if auth_user is None:
            raise UnauthorizedError("Invalid or expired token")
        try:
            return self._ensure_profile_from_auth(auth_user)
        except ConflictError as exc:
            raise UnauthorizedError("User profile could not be loaded") from exc


user_service = UserService()

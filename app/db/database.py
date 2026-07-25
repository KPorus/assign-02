"""PostgreSQL helpers for users and posts (psycopg3)."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings


def _database_url() -> str:
    return get_settings().database_url


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(_database_url(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _user_public(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    data.pop("password", None)
    return data


def _post_with_user(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    user = {
        "id": data.pop("user_id"),
        "username": data.pop("username"),
        "email": data.pop("email"),
        "created_at": data.pop("user_created_at"),
        "updated_at": data.pop("user_updated_at"),
    }
    data["user"] = user
    return data


_POST_SELECT = """
    SELECT
        p.id,
        p.title,
        p.description,
        p.created_at,
        p.updated_at,
        u.id AS user_id,
        u.username,
        u.email,
        u.created_at AS user_created_at,
        u.updated_at AS user_updated_at
    FROM posts p
    JOIN users u ON u.id = p.user_id
"""


def create_table() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )


# --- users ---


def insert_user(
    username: str,
    email: str,
    password: str,
    created_at: datetime,
    updated_at: datetime,
) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO users (username, email, password, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, username, email, created_at, updated_at
            """,
            (username, email, password, created_at, updated_at),
        ).fetchone()
    user = _user_public(row)
    if user is None:
        raise RuntimeError("Failed to load inserted user")
    return user


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, username, email, created_at, updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()
    return _user_public(row)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Return user including password hash for authentication."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, username, email, password, created_at, updated_at
            FROM users
            WHERE email = %s
            """,
            (email,),
        ).fetchone()
    return dict(row) if row is not None else None


def update_user(
    user_id: int,
    username: str | None,
    email: str | None,
    password: str | None,
    updated_at: datetime,
) -> dict[str, Any] | None:
    with get_connection() as conn:
        current = conn.execute(
            "SELECT username, email, password FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
        if current is None:
            return None

        row = conn.execute(
            """
            UPDATE users
            SET username = %s,
                email = %s,
                password = %s,
                updated_at = %s
            WHERE id = %s
            RETURNING id, username, email, created_at, updated_at
            """,
            (
                username if username is not None else current["username"],
                email if email is not None else current["email"],
                password if password is not None else current["password"],
                updated_at,
                user_id,
            ),
        ).fetchone()
    return _user_public(row)


def delete_user(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            DELETE FROM users
            WHERE id = %s
            RETURNING id, username, email, created_at, updated_at
            """,
            (user_id,),
        ).fetchone()
    return _user_public(row)


# --- posts ---


def insert_post(
    user_id: int,
    title: str,
    description: str,
    created_at: datetime,
    updated_at: datetime,
) -> dict[str, Any]:
    with get_connection() as conn:
        inserted = conn.execute(
            """
            INSERT INTO posts (user_id, title, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, title, description, created_at, updated_at),
        ).fetchone()
        row = conn.execute(
            f"{_POST_SELECT} WHERE p.id = %s",
            (inserted["id"],),
        ).fetchone()
    post = _post_with_user(row)
    if post is None:
        raise RuntimeError("Failed to load inserted post")
    return post


def get_posts() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(f"{_POST_SELECT} ORDER BY p.id").fetchall()
    return [_post_with_user(row) for row in rows]  # type: ignore[misc]


def get_post_by_id(post_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            f"{_POST_SELECT} WHERE p.id = %s",
            (post_id,),
        ).fetchone()
    return _post_with_user(row)


def update_post(
    post_id: int,
    title: str | None,
    description: str | None,
    updated_at: datetime,
) -> dict[str, Any] | None:
    with get_connection() as conn:
        current = conn.execute(
            "SELECT title, description FROM posts WHERE id = %s",
            (post_id,),
        ).fetchone()
        if current is None:
            return None

        conn.execute(
            """
            UPDATE posts
            SET title = %s,
                description = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (
                title if title is not None else current["title"],
                description if description is not None else current["description"],
                updated_at,
                post_id,
            ),
        )
        row = conn.execute(
            f"{_POST_SELECT} WHERE p.id = %s",
            (post_id,),
        ).fetchone()
    return _post_with_user(row)


def delete_post(post_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        existing = conn.execute(
            f"{_POST_SELECT} WHERE p.id = %s",
            (post_id,),
        ).fetchone()
        if existing is None:
            return None
        conn.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    return _post_with_user(existing)


def search_posts(
    query: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    filters: list[str] = []
    params: list[Any] = []

    q = (query or "").strip()
    if q:
        filters.append("(p.title ILIKE %s OR p.description ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    offset = (page - 1) * page_size

    with get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS count FROM posts p {where}",
            params,
        ).fetchone()["count"]
        rows = conn.execute(
            f"{_POST_SELECT} {where} ORDER BY p.id LIMIT %s OFFSET %s",
            [*params, page_size, offset],
        ).fetchall()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "items": [_post_with_user(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

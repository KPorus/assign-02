"""PostgreSQL helpers for posts (local Docker Postgres via psycopg3).

Users live in Supabase; posts.user_id stores the Auth UUID with no FK.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator
from uuid import UUID

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


_POST_SELECT = """
    SELECT
        p.id,
        p.user_id,
        p.title,
        p.description,
        p.created_at,
        p.updated_at
    FROM posts p
"""


def create_table() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                user_id UUID NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )


def insert_post(
    user_id: str,
    title: str,
    description: str,
    created_at: datetime,
    updated_at: datetime,
) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO posts (user_id, title, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, user_id, title, description, created_at, updated_at
            """,
            (UUID(user_id), title, description, created_at, updated_at),
        ).fetchone()
    if row is None:
        raise RuntimeError("Failed to load inserted post")
    data = dict(row)
    data["user_id"] = str(data["user_id"])
    return data


def get_posts() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(f"{_POST_SELECT} ORDER BY p.id").fetchall()
    return [_normalize_post(row) for row in rows]


def get_post_by_id(post_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            f"{_POST_SELECT} WHERE p.id = %s",
            (post_id,),
        ).fetchone()
    return _normalize_post(row) if row is not None else None


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

        row = conn.execute(
            """
            UPDATE posts
            SET title = %s,
                description = %s,
                updated_at = %s
            WHERE id = %s
            RETURNING id, user_id, title, description, created_at, updated_at
            """,
            (
                title if title is not None else current["title"],
                description if description is not None else current["description"],
                updated_at,
                post_id,
            ),
        ).fetchone()
    return _normalize_post(row) if row is not None else None


def delete_post(post_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            f"{_POST_SELECT} WHERE p.id = %s",
            (post_id,),
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    return _normalize_post(row)


def delete_posts_by_user_id(user_id: str) -> int:
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM posts WHERE user_id = %s",
            (UUID(user_id),),
        )
    return result.rowcount or 0


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
        "items": [_normalize_post(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def _normalize_post(row: dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    data["user_id"] = str(data["user_id"])
    return data

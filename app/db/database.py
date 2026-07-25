"""PostgreSQL helpers for the tasks table (psycopg3)."""

from __future__ import annotations

from contextlib import contextmanager
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


def _row_to_dict(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    data["completed"] = bool(data["completed"])
    return data


def create_table() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                completed BOOLEAN NOT NULL DEFAULT FALSE
            );
            """
        )


def get_tasks(completed: bool | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if completed is None:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE completed = %s ORDER BY id",
                (completed,),
            ).fetchall()
    return [_row_to_dict(row) for row in rows]  # type: ignore[misc]


def get_task_by_id(task_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = %s",
            (task_id,),
        ).fetchone()
    return _row_to_dict(row)


def insert_task(title: str, description: str, completed: bool) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO tasks (title, description, completed)
            VALUES (%s, %s, %s)
            RETURNING id, title, description, completed
            """,
            (title, description, completed),
        ).fetchone()
    task = _row_to_dict(row)
    if task is None:
        raise RuntimeError("Failed to load inserted task")
    return task


def update_task(
    task_id: int,
    title: str,
    description: str,
    completed: bool,
) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            UPDATE tasks
            SET title = %s, description = %s, completed = %s
            WHERE id = %s
            RETURNING id, title, description, completed
            """,
            (title, description, completed, task_id),
        ).fetchone()
    return _row_to_dict(row)


def delete_task(task_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            DELETE FROM tasks
            WHERE id = %s
            RETURNING id, title, description, completed
            """,
            (task_id,),
        ).fetchone()
    return _row_to_dict(row)


def search_tasks(
    query: str | None = None,
    completed: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    filters: list[str] = []
    params: list[Any] = []

    q = (query or "").strip()
    if q:
        filters.append("(title ILIKE %s OR description ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like])

    if completed is not None:
        filters.append("completed = %s")
        params.append(completed)

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    offset = (page - 1) * page_size

    with get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS count FROM tasks {where}",
            params,
        ).fetchone()["count"]
        rows = conn.execute(
            f"SELECT * FROM tasks {where} ORDER BY id LIMIT %s OFFSET %s",
            [*params, page_size, offset],
        ).fetchall()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "items": [_row_to_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

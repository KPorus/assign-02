from datetime import datetime

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db import database as db
from app.schemas.post import PostCreate, PostResponse, PostSearchResult, PostUpdate
from app.schemas.user import UserResponse
from app.services.user_service import user_service


def _to_post(row: dict, user: UserResponse) -> PostResponse:
    return PostResponse(
        id=row["id"],
        user=user,
        title=row["title"],
        description=row["description"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class PostService:
    def create(self, payload: PostCreate, user_id: str) -> PostResponse:
        row = db.insert_post(
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        authors = user_service.resolve_authors([user_id])
        return _to_post(row, authors[user_id])

    def list_posts(self) -> list[PostResponse]:
        rows = db.get_posts()
        authors = user_service.resolve_authors([row["user_id"] for row in rows])
        return [_to_post(row, authors[row["user_id"]]) for row in rows]

    def search(
        self,
        *,
        q: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PostSearchResult:
        result = db.search_posts(
            query=q,
            page=page,
            page_size=page_size,
        )
        items = result["items"]
        authors = user_service.resolve_authors([row["user_id"] for row in items])
        return PostSearchResult(
            items=[_to_post(item, authors[item["user_id"]]) for item in items],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"],
        )

    def get(self, post_id: int) -> PostResponse:
        row = db.get_post_by_id(post_id)
        if row is None:
            raise NotFoundError(f"Post with id {post_id} not found")
        authors = user_service.resolve_authors([row["user_id"]])
        return _to_post(row, authors[row["user_id"]])

    def update(self, post_id: int, payload: PostUpdate, user_id: str) -> PostResponse:
        existing = self.get(post_id)
        if existing.user.id != user_id:
            raise ForbiddenError("You can only update your own posts")
        row = db.update_post(
            post_id,
            payload.title,
            payload.description,
            updated_at=datetime.now(),
        )
        if row is None:
            raise NotFoundError(f"Post with id {post_id} not found")
        authors = user_service.resolve_authors([row["user_id"]])
        return _to_post(row, authors[row["user_id"]])

    def delete(self, post_id: int, user_id: str) -> PostResponse:
        existing = self.get(post_id)
        if existing.user.id != user_id:
            raise ForbiddenError("You can only delete your own posts")
        row = db.delete_post(post_id)
        if row is None:
            raise NotFoundError(f"Post with id {post_id} not found")
        return existing


post_service = PostService()

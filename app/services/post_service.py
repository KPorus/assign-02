from app.core.exceptions import NotFoundError
from app.db import database as db
from app.schemas.post import PostCreate, PostResponse, PostUpdate
from datetime import datetime
from app.schemas.user import UserResponse

def _to_post(row: dict) -> PostResponse:
    return PostResponse.model_validate(row)


class PostService:
    def create(self, payload: PostCreate) -> PostResponse:
        row = db.insert_post(
            user_id=payload.user.id,
            title=payload.title,
            description=payload.description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return _to_post(row)

    def list_posts(self) -> list[PostResponse]:
        rows = db.get_posts()
        return [_to_post(row) for row in rows]

    def search(
        self,
        *,
        q: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> list[PostResponse]:
        result = db.search_posts(
            query=q,
            page=page,
            page_size=page_size,
        )
        return [_to_post(item) for item in result["items"]]

    def get(self, post_id: int) -> PostResponse:
        row = db.get_post_by_id(post_id)
        if row is None:
            raise NotFoundError(f"Post with id {post_id} not found")
        return _to_post(row)

    def update(self, post_id: int, payload: PostUpdate) -> PostResponse:
        row = db.update_post(
            post_id,
            payload.title,
            payload.description,
            updated_at=datetime.now(),
        )
        if row is None:
            raise NotFoundError(f"Post with id {post_id} not found")
        return _to_post(row)

    def delete(self, post_id: int) -> PostResponse:
        row = db.delete_post(post_id)
        if row is None:
            raise NotFoundError(f"Post with id {post_id} not found")
        return _to_post(row)


post_service = PostService()

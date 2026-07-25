from fastapi import APIRouter, Depends, Path, Query, Request, status

from app.config import get_settings
from app.core.rate_limit import limiter
from app.core.responses import success_response
from app.dependencies import get_post_service
from app.schemas.post import PostCreate, PostUpdate
from app.services.post_service import PostService

router = APIRouter(prefix="/posts", tags=["posts"])
settings = get_settings()


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_write)
async def create_post(
    request: Request,
    payload: PostCreate,
    service: PostService = Depends(get_post_service),
):
    post = service.create(payload)
    return success_response(
        data=post.model_dump(),
        message="Post created successfully",
        status_code=status.HTTP_201_CREATED,
    )


@router.get("")
@limiter.limit(settings.rate_limit_default)
async def list_posts(
    request: Request,
    service: PostService = Depends(get_post_service),
):
    posts = service.list_posts()
    return success_response(
        data=[post.model_dump() for post in posts],
        message="Posts retrieved successfully",
    )


@router.get("/search")
@limiter.limit(settings.rate_limit_default)
async def search_posts(
    request: Request,
    q: str | None = Query(default=None, max_length=200, description="Search in title and description"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    service: PostService = Depends(get_post_service),
):
    result = service.search(q=q, page=page, page_size=page_size)
    return success_response(
        data=result.model_dump(),
        message="Posts searched successfully",
    )


@router.get("/{post_id}")
@limiter.limit(settings.rate_limit_default)
async def get_post(
    request: Request,
    post_id: int = Path(..., gt=0),
    service: PostService = Depends(get_post_service),
):
    post = service.get(post_id)
    return success_response(
        data=post.model_dump(),
        message="Post retrieved successfully",
    )


@router.put("/{post_id}")
@limiter.limit(settings.rate_limit_write)
async def update_post(
    request: Request,
    payload: PostUpdate,
    post_id: int = Path(..., gt=0),
    service: PostService = Depends(get_post_service),
):
    post = service.update(post_id, payload)
    return success_response(
        data=post.model_dump(),
        message="Post updated successfully",
    )


@router.delete("/{post_id}")
@limiter.limit(settings.rate_limit_write)
async def delete_post(
    request: Request,
    post_id: int = Path(..., gt=0),
    service: PostService = Depends(get_post_service),
):
    post = service.delete(post_id)
    return success_response(
        data=post.model_dump(),
        message="Post deleted successfully",
    )

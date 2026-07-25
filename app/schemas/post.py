from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserResponse


class PostResponse(BaseModel):
    id: int
    user: UserResponse
    title: str
    description: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    model_config = {"from_attributes": True}


class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class PostSearchResult(BaseModel):
    items: list[PostResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

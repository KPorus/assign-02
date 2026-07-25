from pydantic import BaseModel, Field
from datetime import datetime
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
    user: UserResponse
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PostUpdate(BaseModel):
    user: UserResponse
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=2000)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PostSearchResult(BaseModel):
    items: list[PostResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

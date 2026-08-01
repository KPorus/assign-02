from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=20)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthResult(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class UserSearchResult(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

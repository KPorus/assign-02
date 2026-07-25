from pydantic import BaseModel, Field
from datetime import datetime

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    model_config = {"from_attributes": True}

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=20)
    email: str = Field(..., format="email")
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    username: str = Field(..., min_length=1, max_length=20)
    email: str = Field(..., format="email")
    password: str = Field(..., min_length=8)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
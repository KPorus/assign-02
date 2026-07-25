from fastapi import APIRouter, Depends, Path, Query, Request, status

from app.config import get_settings
from app.core.rate_limit import limiter
from app.core.responses import success_response
from app.dependencies import get_user_service
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()

@router.post("/create", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_write)
async def create_user(
    request: Request,
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
):
    user = service.create(payload)
    return success_response(
        data=user.model_dump(),
        message="User created successfully",
        status_code=status.HTTP_201_CREATED,
    )

@router.get("/get/{user_id}", status_code=status.HTTP_200_OK)
@limiter.limit(settings.rate_limit_default)
async def get_user(request: Request, user_id: int = Path(..., gt=0), service: UserService = Depends(get_user_service)):
    user = service.get(user_id)
    return success_response(data=user.model_dump(), message="User retrieved successfully",status_code=status.HTTP_200_OK)

@router.put("/update/{user_id}", status_code=status.HTTP_200_OK)
@limiter.limit(settings.rate_limit_write)
async def update_user(request: Request, payload: UserUpdate, user_id: int = Path(..., gt=0), service: UserService = Depends(get_user_service)):
    user = service.update(user_id, payload)
    return success_response(data=user.model_dump(), message="User updated successfully",status_code=status.HTTP_200_OK)

@router.delete("/delete/{user_id}", status_code=status.HTTP_200_OK)
@limiter.limit(settings.rate_limit_write)
async def delete_user(request: Request, user_id: int = Path(..., gt=0), service: UserService = Depends(get_user_service)):
    user = service.delete(user_id)
    return success_response(data=user.model_dump(), message="User deleted successfully",status_code=status.HTTP_200_OK)
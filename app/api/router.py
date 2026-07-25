from fastapi import APIRouter

from app.api.routes import auth, health, post, user

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(post.router)
api_router.include_router(user.router)

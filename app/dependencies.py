from app.services.user_service import UserService, user_service


def get_post_service() -> PostService:
    return post_service

def get_user_service() -> UserService:
    return user_service
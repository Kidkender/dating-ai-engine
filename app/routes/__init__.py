from fastapi import APIRouter

from .sync_route import sync_router

from .user_route import user_router
from .pool_image_route import pool_image_router
from .user_choice_route import choice_router
from .recommendation_route import recommendation_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(user_router)
api_v1_router.include_router(sync_router)
api_v1_router.include_router(pool_image_router)
api_v1_router.include_router(choice_router)
api_v1_router.include_router(recommendation_router)
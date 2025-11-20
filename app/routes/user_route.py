from fastapi import APIRouter, status

from ..core.dependency import UserServiceDep
from app.schemas.user import UserCreate, UserResponse

user_router = APIRouter(prefix="/users", tags=["users"])



@user_router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register_user(user_data: UserCreate, 
                  service: UserServiceDep
                  ):
    return service.create_user( user_data)

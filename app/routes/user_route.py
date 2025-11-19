from fastapi import APIRouter, status, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService

user_router = APIRouter(prefix="/users", tags=["users"])

def __get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

@user_router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register_user(user_data: UserCreate, 
                  service: UserService = Depends(__get_user_service)
                  ):
    return service.create_user( user_data)

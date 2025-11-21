import secrets
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.database import transactional
from app.core.exception import AppException
from app.schemas.user import UserCreate, UserResponse, UserStatus
from app.models.user import User
from app.constants.error_constant import ERROR_USER_DUPLICATE_EMAIL, ERROR_USER_NOT_FOUND
from fastapi import status
import logging


logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user operations"""
    
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def generate_session_token() -> str:

        return secrets.token_urlsafe(32)

    def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user

        Args:
            db: Database session
            user_data: User creation data

        Returns:
            Created user instance

        Raises:
            DuplicateEmailError: If email already exists
        """
        with transactional(self.db):
            existing_user = self.db.query(User).filter(User.email == user_data.email).first()
            if existing_user:
                raise AppException(ERROR_USER_DUPLICATE_EMAIL)

            session_token = UserService.generate_session_token()

            db_user = User(
                email=user_data.email,
                name=user_data.name,
                gender=user_data.gender,
                session_token=session_token,
                status=UserStatus.ONBOARDING,
            )

            self.db.add(db_user)
            self.db.flush()
            self.db.refresh(db_user)
            return UserResponse.model_validate(db_user)

    def get_user_by_id(self, user_id: UUID) -> User | None :
        exist_user = self.db.query(User).filter(User.id == user_id).first()
        if exist_user is None:
          raise AppException(
              error_code=ERROR_USER_NOT_FOUND,
              status_code=status.HTTP_404_NOT_FOUND
          )
        return exist_user
    
    def get_user_by_external_id(self, external_user_id: str) -> User | None :
        exist_user = self.db.query(User).filter(User.external_user_id == external_user_id).first()
        return exist_user
        
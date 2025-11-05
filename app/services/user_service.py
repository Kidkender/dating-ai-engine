import secrets
from sqlalchemy.orm import Session
from app.core.database import transactional
from app.core.exception import BadRequestException
from app.schemas.user import UserCreate, UserStatus
from app.models.user import User
from app.utils.error_constant import ERROR_USER_DUPLICATE_EMAIL
import logging


logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user operations"""

    @staticmethod
    def generate_session_token() -> str:

        return secrets.token_urlsafe(32)

    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
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
        with transactional(db):
            existing_user = db.query(User).filter(User.email == user_data.email).first()
            if existing_user:
                raise BadRequestException(ERROR_USER_DUPLICATE_EMAIL)

            session_token = UserService.generate_session_token()

            db_user = User(
                email=user_data.email,
                name=user_data.name,
                gender=user_data.gender,
                session_token=session_token,
                status=UserStatus.ONBOARDING,
            )

            db.add(db_user)
            db.flush()
            db.refresh(db_user)
            return db_user

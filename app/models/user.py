import uuid
from sqlalchemy import Column, DateTime, Enum, Index, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from sqlalchemy.dialects.postgresql import UUID
import enum
from app.core.database import Base


class Gender(enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class UserStatus(enum.Enum):
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    session_token = Column(String(255), unique=True, nullable=True, index=True)
    name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    gender = Column(Enum(Gender), nullable=True)
    status = Column(Enum(UserStatus))
    external_user_id = Column(String(255), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user_images = relationship(
        "UserImage", back_populates="user", cascade="all, delete-orphan"
    )
    user_choices = relationship(
        "UserChoice", back_populates="user", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_external_user_id', 'external_user_id'),
    )


    def __repr__(self):
        return f"<User(id={self.id}, session={self.session_token[:8]}..., status{self.status})"

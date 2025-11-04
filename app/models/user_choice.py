import uuid
from pgvector import Vector  # type: ignore
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from app.core.database import Base

from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum


class ChoiceType(enum.Enum):
    LIKE = "like"
    PASS = "pass"
    PREFER = "prefer"


class UserChoice(Base):
    __tablename__ = "user_choices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    pool_image_id = Column(
        UUID(as_uuid=True), ForeignKey("pool_images.id"), nullable=False
    )

    phase = Column(Integer, nullable=False, default=1)
    position_in_phase = Column(Integer, nullable=False, default=1)

    action = Column(Enum(ChoiceType), nullable=False)

    response_time_ms = Column(Integer, nullable=True)
    is_revised = Column(Boolean, default=True)
    original_action = Column(Enum(ChoiceType), nullable=True)
    revision_count = Column(Integer, default=0)

    shown_with_images = Column(ARRAY(UUID), nullable=True)  # type: ignore
    ui_interaction = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())  # type: ignore
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="user_choices")
    pool_image = relationship("PoolImage", back_populates="user_choices")

    __table_args__ = (
        UniqueConstraint("user_id", "pool_image_id", name="unique_user_pool_image"),
        CheckConstraint("phase IN (1, 2, 3)", name="check_phase"),
        CheckConstraint(
            "position_in_phase >= 1 AND position_in_phase <= 20", name="check_position"
        ),
        CheckConstraint("response_time_ms > 0", name="check_response_time"),
    )

    def __repr__(self):
        return f"<UserChoice(user={self.user_id}, image={self.pool_image_id}, phase={self.phase}, action={self.action})>"

import enum
import uuid
from sqlalchemy import (
    UUID,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector  # type: ignore
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

Base = declarative_base()


class ImageStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UserImage(Base):
    __tablename__ = "user_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())

    image_URL = Column(Text, nullable=False)

    face_embedding = Column(Vector(512), nullable=True)  # type: ignore
    face_confidence = Column(Float, nullable=True)  # type: ignore
    facial_attributes = Column(JSONB, nullable=True)
    is_primary = Column(Boolean, default=False)
    processing_status = Column(Enum(ImageStatus), default=ImageStatus.PENDING)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user = relationship("User", back_populates="user_images")

    __table_args__ = (
        CheckConstraint(
            "face_confidence >= 0 AND face_confidence <= 1",
            name="check_face_confidence",
        ),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'completed', 'failed')",
            name="check_processing_status",
        ),
    )

    def __repr__(self):
        return f"<UserImage(id={self.id}, user_id={self.user_id}, primary={self.is_primary})>"

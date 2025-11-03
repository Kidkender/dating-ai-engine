import uuid
from pgvector import Vector  # type: ignore
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB


Base = declarative_base()


class PoolImage(Base):
    __table_name__ = "pool_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4())
    image_URL = Column(Text, nullable=False, unique=True)

    person_code = Column(String(50), nullable=True)  # Anonymous identifier
    person_name = Column(String(100), nullable=True)  # Optional model/person name
    person_gender = Column(String(20), nullable=True)
    person_age_range = Column(String(20), nullable=True)  # '18-25', '25-35', etc.

    # Face Analysis (same as user_images)
    face_embedding = Column(Vector(512), nullable=False)  # type: ignore
    face_confidence = Column(Float, nullable=False)  # type: ignore
    facial_attributes = Column(JSONB, nullable=False)
    # Same structure as UserImage.facial_attributes

    # Categorization for diversity
    diversity_tags = Column(JSONB, nullable=True)

    phase_eligibility = Column(
        ARRAY(Integer()), default=[1, 2, 3]
    )  # Which phases can show this
    phase_1_priority = Column(Integer, default=5)
    phase_2_priority = Column(Integer, default=5)
    phase_3_priority = Column(Integer, default=5)

    usage_count = Column(Integer, default=0)  # Total times shown to any user
    like_count = Column(Integer, default=0)  # Total likes received
    pass_count = Column(Integer, default=0)  # Total passes received
    prefer_count = Column(Integer, default=0)  # Total prefers received
    avg_response_time = Column(Float, nullable=True)  # type: ignore

    quality_score = Column(Float, nullable=True)  # type: ignore
    is_active = Column(Boolean, default=True)  # Soft delete / disable
    disabled_reason = Column(String(200), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_shown_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "face_confidence >= 0 AND face_confidence <= 1",
            name="check_pool_face_confidence",
        ),
        CheckConstraint(
            "quality_score >= 0 AND quality_score <= 10", name="check_quality_score"
        ),
        CheckConstraint(
            "phase_1_priority >= 1 AND phase_1_priority <= 10",
            name="check_phase1_priority",
        ),
        CheckConstraint(
            "phase_2_priority >= 1 AND phase_2_priority <= 10",
            name="check_phase2_priority",
        ),
        CheckConstraint(
            "phase_3_priority >= 1 AND phase_3_priority <= 10",
            name="check_phase3_priority",
        ),
    )

    def __repr__(self):
        return f"<PoolImage(id={self.id}, person={self.person_code}, active={self.is_active})>"

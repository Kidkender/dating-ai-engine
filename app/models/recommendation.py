import uuid
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Recommendation(Base):
    """Store personalized recommendations for users"""
    
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User who receives the recommendation
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # User being recommended
    recommended_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Similarity score (0-1, higher is better match)
    similarity_score = Column(Float, nullable=False)
    
    # Ranking (1 = best match)
    rank = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="received_recommendations")
    recommended_user = relationship("User", foreign_keys=[recommended_user_id], backref="given_recommendations")
    
    __table_args__ = (
        UniqueConstraint("user_id", "recommended_user_id", name="unique_user_recommendation"),
    )

    def __repr__(self):
        return f"<Recommendation(user={self.user_id}, recommended={self.recommended_user_id}, score={self.similarity_score:.3f}, rank={self.rank})>"
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class PoolImageBase(BaseModel):
    """Base pool image schema"""

    image_URL: str
    person_code: str
    face_confidence: float


class PoolImageResponse(PoolImageBase):
    """Response schema for pool image"""

    id: UUID
    phase_eligibility: list[int]
    is_active: bool
    usage_count: int = 0
    like_count: int = 0
    pass_count: int = 0
    prefer_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ImportSummary(BaseModel):
    """Summary for import operation"""

    message: str
    round1: dict = Field(default_factory=dict)
    round2: dict = Field(default_factory=dict)
    round3: dict = Field(default_factory=dict)
    errors: list[dict] = Field(default_factory=list)


class PhaseImagesResponse(BaseModel):
    """Response for getting phase images"""

    phase: int
    total_images: int
    images: list[PoolImageResponse]

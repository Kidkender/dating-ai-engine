from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ChoiceSubmitRequest(BaseModel):
    """Request to submit a choice"""

    pool_image_id: UUID
    action: str = Field(..., description="LIKE, PASS, or PREFER")
    response_time_ms: Optional[int] = Field(None, ge=0, description="Response time in milliseconds")


class ChoiceSubmitResponse(BaseModel):
    """Response after submitting a choice"""

    message: str = "Choice recorded successfully"
    choice_id: str
    current_phase: int
    phase_progress: str
    total_choices: int
    all_completed: bool


class UserProgressResponse(BaseModel):
    """Response for user progress"""

    user_id: str
    current_phase: int
    phase_progress: str
    total_choices: int
    phase_1_completed: bool
    phase_1_count: int
    phase_2_completed: bool
    phase_2_count: int
    phase_3_completed: bool
    phase_3_count: int
    all_completed: bool


class PoolImageInfo(BaseModel):
    """Pool image info in choice response"""

    id: str
    image_url: str
    person_code: str


class UserChoiceResponse(BaseModel):
    """Single choice response"""

    id: str
    pool_image: PoolImageInfo
    action: str
    phase: int
    position: int
    response_time_ms: Optional[int]
    created_at: Optional[str]


class ChoiceStatistics(BaseModel):
    """Statistics for user choices"""

    likes: int
    passes: int
    prefers: int


class UserChoicesListResponse(BaseModel):
    """Response for list of user choices"""

    total: int
    phase_filter: Optional[int]
    choices: list[UserChoiceResponse]
    statistics: ChoiceStatistics
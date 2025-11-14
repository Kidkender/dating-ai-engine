from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ChoiceSubmitRequest(BaseModel):
    """Request to submit a choice"""

    pool_image_id: UUID
    action: str = Field(..., description="LIKE, PASS, or PREFER")
    response_time_ms: Optional[int] = Field(None, ge=0, description="Response time in milliseconds")


class SingleChoiceItem(BaseModel):
    """Single choice item for batch submission"""
    
    pool_image_id: UUID
    action: str = Field(..., description="LIKE, PASS, or PREFER")
    response_time_ms: Optional[int] = Field(None, ge=0, description="Response time in milliseconds")
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action is one of LIKE, PASS, PREFER"""
        if v.upper() not in ['LIKE', 'PASS', 'PREFER']:
            raise ValueError('Action must be LIKE, PASS, or PREFER')
        return v.upper()


class BatchChoiceSubmitRequest(BaseModel):
    """Request to submit multiple choices at once"""
    
    choices: list[SingleChoiceItem] = Field(
        ..., 
        min_length=20, 
        max_length=20,
        description="Must submit exactly 20 choices for a phase"
    )
    
    @field_validator('choices')
    @classmethod
    def validate_choices_count(cls, v: list) -> list:
        """Validate exactly 20 choices"""
        if len(v) != 20:
            raise ValueError('Must submit exactly 20 choices for a phase')
        return v


class ChoiceSubmitResponse(BaseModel):
    """Response after submitting a choice"""

    message: str = "Choice recorded successfully"
    choice_id: str
    current_phase: int
    phase_progress: str
    total_choices: int
    all_completed: bool


class ChoiceStatisticsResponse(BaseModel):
    """Statistics for batch choices"""
    
    likes: int
    passes: int
    prefers: int


class BatchChoiceSubmitResponse(BaseModel):
    """Response after submitting batch choices"""
    
    message: str
    success: bool
    choices_created: int
    phase_completed: int
    current_phase: int
    phase_progress: str
    total_choices: int
    all_completed: bool
    statistics: ChoiceStatisticsResponse


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
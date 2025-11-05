from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class UserStatus(str, Enum):
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class UserBase(BaseModel):
    """Base user schema"""

    email: EmailStr
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[Gender] = None


class UserCreate(UserBase):
    """Schema for creating a new user"""

    pass


class UserUpdate(BaseModel):
    """Schema for updating user information"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    gender: Optional[Gender] = None
    status: Optional[UserStatus] = None


class UserImageResponse(BaseModel):
    """Response schema for user images"""

    id: UUID
    image_URL: str
    is_primary: bool
    face_confidence: Optional[float] = None
    processing_status: str
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    """Response schema for user"""

    id: UUID
    session_token: str
    status: UserStatus
    created_at: datetime
    last_active: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Optional: Include user images in response
    user_images: Optional[list[UserImageResponse]] = None

    class Config:
        from_attributes = True


class UserPublicResponse(BaseModel):
    """Public user response (without sensitive data)"""

    id: UUID
    name: Optional[str] = None
    status: UserStatus
    created_at: datetime

    class Config:
        from_attributes = True


class UserLoginRequest(BaseModel):
    """Schema for user login"""

    email: EmailStr


class UserLoginResponse(BaseModel):
    """Schema for user login response"""

    user: UserResponse
    session_token: str
    message: str = "Login successful"


class SessionTokenRequest(BaseModel):
    """Request with session token"""

    session_token: str = Field(..., min_length=1)


class UserStatistics(BaseModel):
    """User statistics response"""

    total_choices: int = 0
    phases_completed: int = 0
    current_phase: int = 1
    likes_count: int = 0
    passes_count: int = 0
    prefers_count: int = 0
    images_processed: int = 0
    last_activity: Optional[datetime] = None

import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class DatingAppResponse(BaseModel):
    """Wrapper response from dating app API"""

    status: int
    message: str = ""
    data: list[dict[str, Any]] = Field(default_factory=list)  # type: ignore

    model_config = {"extra": "ignore"}


class DatingAppUser(BaseModel):
    """Schema for user data from dating app API"""

    # MongoDB ID
    id: Optional[str] = Field(None, alias="_id")

    # User Info
    userName: Optional[str] = None
    userSurname: Optional[str] = None
    fullName: Optional[str] = None
    userEmail: str
    userGender: Optional[str] = None  # "male", "female"
    userBirthdate: Optional[str] = None  # ISO date string
    userSlug: Optional[str] = None
    userAddress: Optional[str] = None

    # Images
    userImages: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"

    @property
    def name(self) -> Optional[str]:
        """Get full name or construct from userName + userSurname"""
        if self.fullName:
            return self.fullName
        if self.userName and self.userSurname:
            return f"{self.userName} {self.userSurname}"
        return self.userName or self.userSurname

    @property
    def email(self) -> str:
        """Get email"""
        return self.userEmail

    @property
    def gender(self) -> Optional[str]:
        """Get gender in uppercase format (MALE/FEMALE)"""
        if self.userGender:
            return self.userGender.upper()
        return None

    @property
    def images(self) -> list[str]:
        """Get list of image URLs"""
        return self.userImages

    @property
    def age(self) -> Optional[int]:
        """Calculate age from birthdate"""
        if not self.userBirthdate:
            return None
        try:
            from datetime import datetime

            birthdate = datetime.fromisoformat(
                self.userBirthdate.replace("Z", "+00:00")
            )
            today = datetime.now()
            age = (
                today.year
                - birthdate.year
                - ((today.month, today.day) < (birthdate.month, birthdate.day))
            )
            return age
        except Exception:
            return None


class ImageProcessingResult(BaseModel):
    """Result of processing a single image"""

    image_url: str
    success: bool
    face_detected: bool = False
    face_confidence: Optional[float] = None
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None


class UserSyncResult(BaseModel):
    """Result of syncing a single user"""

    user_id: Optional[UUID] = None
    email: str
    success: bool
    images_processed: int = 0
    images_with_faces: int = 0
    is_active: bool = False
    error_message: Optional[str] = None
    image_results: list[ImageProcessingResult] = Field(default_factory=list)  # type: ignore


class SyncSummary(BaseModel):
    """Overall sync summary report"""

    sync_timestamp: datetime.datetime  # type: ignore
    total_users_pulled: int = 0
    users_synced: int = 0
    users_skipped: int = 0
    users_with_valid_faces: int = 0
    users_without_faces: int = 0
    total_images_processed: int = 0
    faces_detected: int = 0
    faces_failed: int = 0
    avg_confidence: Optional[float] = None
    total_duration_seconds: Optional[float] = None
    errors: list[dict] = Field(default_factory=list)  # type: ignore
    warnings: list[dict] = Field(default_factory=list)  # type: ignore

    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    """Request schema for sync operation"""

    limit: Optional[int] = Field(
        10, ge=1, le=1000, description="Limit number of users to sync"
    )
    force_resync: bool = Field(False, description="Force resync existing users")
    min_face_confidence: float = Field(
        0.80, ge=0.0, le=1.0, description="Minimum face confidence threshold"
    )


class SyncResponse(BaseModel):
    """Response schema for sync operation"""

    message: str
    summary: SyncSummary
    user_results: list[UserSyncResult] = Field(default_factory=list)  # type: ignore

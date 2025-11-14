import datetime
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class DatingAppResponse(BaseModel):
    """Wrapper response from dating app API"""

    status: int
    message: str = ""
    data: list[dict[str, Any]] = Field(default_factory=list)  # type: ignore

    model_config = {"extra": "ignore"}


class UserInfo(BaseModel):
    """Nested user information"""

    userName: Optional[str] = None
    userEmail: Optional[str] = None
    userGender: Optional[str] = None


class DatingAppUser(BaseModel):
    """Schema for user data from dating app API"""

    # MongoDB ID
    id: Optional[str] = Field(None, alias="_id")

    # id: Optional[str] = Field(None, alias="_id")
    userId: Optional[str] = None
    orientation: Optional[str] = None
    datingImages: List[str] = Field(default_factory=list)
    user: Optional[UserInfo] = None

    # Images
    userImages: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
        populate_by_name = True
        extra = "ignore"

    @property
    def name(self) -> Optional[str]:
        """Get name"""
        return self.user.userName if self.user else None

    @property
    def email(self) -> Optional[str]:
        """Get email"""
        return self.user.userEmail if self.user else None

    @property
    def gender(self) -> Optional[str]:
        """Get gender in uppercase format"""
        if self.user and self.user.userGender:
            return self.user.userGender.upper()
        return None

    @property
    def images(self) -> List[str]:
        """Get list of image URLs"""
        return self.datingImages

    @property
    def primary_image(self) -> Optional[str]:
        """Get the first image if available"""
        return self.datingImages[0] if self.datingImages else None

    @property
    def orientation_upper(self) -> Optional[str]:
        """Return orientation in uppercase"""
        return self.orientation.upper() if self.orientation else None


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

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.services.dating_app_client import DatingAppClient
from app.services.face_processing_service import FaceProcessingService
from app.services.image_sync_service import ImageSyncService
from ..services.pool_image_service import PoolImageService
from ..services.user_choice_service import UserChoiceService
from ..services.recommendation_service import RecommendationService
from ..services.user_service import UserService
from app.services.user_sync_service import UserSyncService
from app.services.orchestrators.sync_orchestrator import SyncOrchestrator


_dating_app_client: DatingAppClient | None = None
_face_processor: FaceProcessingService | None = None


def get_dating_app_client() -> DatingAppClient:
    """Get singleton dating app client"""
    global _dating_app_client
    if _dating_app_client is None:
        _dating_app_client = DatingAppClient(
            base_url=settings.DATING_APP_BASE_URL or "",
            image_base_url=settings.DATING_APP_IMAGE_BASE_URL or "",
            api_key=settings.DATING_APP_API_KEY,
            timeout=settings.DATING_APP_TIMEOUT,
        )
    return _dating_app_client


def get_face_processor() -> FaceProcessingService:
    """Get singleton face processor"""
    global _face_processor
    if _face_processor is None:
        _face_processor = FaceProcessingService(
            min_confidence=settings.MIN_FACE_CONFIDENCE
        )
    return _face_processor


def get_image_sync_service(
    db: Session = Depends(get_db),
    dating_app_client: DatingAppClient = Depends(get_dating_app_client),
    face_processor: FaceProcessingService = Depends(get_face_processor),
) -> ImageSyncService:
    """Get image sync service instance"""
    return ImageSyncService(
        db=db,
        dating_app_client=dating_app_client,
        face_processor=face_processor,
    )


def get_user_sync_service(
    db: Session = Depends(get_db),
    image_sync_service: ImageSyncService = Depends(get_image_sync_service),
) -> UserSyncService:
    """Get user sync service instance"""
    return UserSyncService(
        db=db,
        image_sync_service=image_sync_service,
    )


def get_sync_orchestrator(
    dating_app_client: DatingAppClient = Depends(get_dating_app_client),
    user_sync_service: UserSyncService = Depends(get_user_sync_service),
) -> SyncOrchestrator:
    """Get sync orchestrator instance"""
    return SyncOrchestrator(
        dating_app_client=dating_app_client,
        user_sync_service=user_sync_service,
    )

def get_user_service(
    db: Annotated[Session, Depends(get_db)]
) -> UserService: 
    return UserService(db)

def get_recommendation_service(
    db: Annotated[Session, Depends(get_db)]
) -> RecommendationService:
    return RecommendationService(db)

def get_user_choice_service(
    db: Annotated[Session, Depends(get_db)]
) -> UserChoiceService:
    return UserChoiceService(db)    

def get_pool_image_service(
    db: Annotated[Session, Depends(get_db)]
) -> PoolImageService:
    return PoolImageService(db)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
RecommendationServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]
UserChoiceServiceDep = Annotated[UserChoiceService, Depends(get_user_choice_service)]
PoolImageServiceDep = Annotated[PoolImageService, Depends(get_pool_image_service)]
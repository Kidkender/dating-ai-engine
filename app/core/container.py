from dependency_injector import containers, providers
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.dating_app_client import DatingAppClient
from app.services.face_processing_service import FaceProcessingService
from app.services.image_sync_service import ImageSyncService
from app.services.user_sync_service import UserSyncService
from app.services.orchestrators.sync_orchestrator import SyncOrchestrator


class Container(containers.DeclarativeContainer):
    """Application DI Container"""

    config = providers.Configuration()

    db_session = providers.Dependency(instance_of=Session)

    dating_app_client = providers.Singleton(
        DatingAppClient,
        base_url=settings.DATING_APP_BASE_URL,
        image_base_url=settings.DATING_APP_IMAGE_BASE_URL,
        api_key=settings.DATING_APP_API_KEY,
        timeout=settings.DATING_APP_TIMEOUT,
    )

    face_processor = providers.Singleton(
        FaceProcessingService,
        min_confidence=settings.MIN_FACE_CONFIDENCE,
    )

    image_sync_service = providers.Factory(
        ImageSyncService,
        db=db_session,
        dating_app_client=dating_app_client,
        face_processor=face_processor,
    )

    user_sync_service = providers.Factory(
        UserSyncService,
        db=db_session,
        image_sync_service=image_sync_service,
    )

    sync_orchestrator = providers.Factory(
        SyncOrchestrator,
        dating_app_client=dating_app_client,
        user_sync_service=user_sync_service,
    )


container = Container()

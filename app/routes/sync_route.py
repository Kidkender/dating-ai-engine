from datetime import datetime
import logging

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.sync import SyncRequest, SyncResponse, SyncSummary
from app.services.dating_app_client import DatingAppClient
from app.services.face_processing_service import FaceProcessingService
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

sync_router = APIRouter(prefix="/sync", tags=["sync"])


def get_sync_service(db: Session = Depends(get_db)) -> SyncService:
    """Dependency to get sync service instance"""
    base_url = settings.DATING_APP_BASE_URL or ""
    image_base_url = settings.DATING_APP_IMAGE_BASE_URL or ""

    # Initialize dating app client from settings
    dating_app_client = DatingAppClient(
        base_url=base_url,
        image_base_url=image_base_url,
        api_key=settings.DATING_APP_API_KEY,
        timeout=settings.DATING_APP_TIMEOUT,
    )

    # Initialize face processor from settings
    face_processor = FaceProcessingService(min_confidence=settings.MIN_FACE_CONFIDENCE)

    # Create sync service
    sync_service = SyncService(
        dating_app_client=dating_app_client, face_processor=face_processor, db=db
    )

    return sync_service


@sync_router.post(
    "/users",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync users from dating app",
    description="Pull users from dating app and process their images for face detection",
)
async def sync_users(
    sync_request: SyncRequest = Body(
        default=SyncRequest(limit=100, force_resync=False, min_face_confidence=0.8)
    ),
    sync_service: SyncService = Depends(get_sync_service),
):
    """
    Sync users from dating app to AI engine

    - **limit**: Optional limit on number of users to sync (1-1000)
    - **force_resync**: Force resync existing users (default: False)
    - **min_face_confidence**: Minimum face confidence threshold (0.0-1.0, default: 0.80)

    Returns detailed sync summary including:
    - Total users processed
    - Successful syncs
    - Face detection statistics
    - Errors and warnings
    """
    try:
        logger.info(f"Starting sync with request: {sync_request}")

        summary = await sync_service.sync_users_from_dating_app(sync_request)
        response = SyncResponse(
            message=f"Sync completed: {summary.users_synced}/{summary.total_users_pulled} users synced",
            summary=summary,
        )

        return response

    except Exception as e:
        logger.error(f"Error in sync endpoint: {e}")
        # Return partial results with error
        error_summary = SyncSummary(
            sync_timestamp=(
                summary.sync_timestamp if "summary" in locals() else datetime.now()
            ),
            errors=[
                {"error": f"Sync endpoint error: {str(e)}", "timestamp": datetime.now()}
            ],
        )
        return SyncResponse(message=f"Sync failed: {str(e)}", summary=error_summary)


@sync_router.post(
    "/images/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete synced image",
    description="Delete an image that was removed from dating app",
)
async def delete_synced_image(
    image_url: str = Body(..., embed=True),
    sync_service: SyncService = Depends(get_sync_service),
):
    """
    Delete a synced image

    - **image_url**: Image URL/filename to delete

    This endpoint should be called when an image is deleted from the dating app
    """
    try:
        success = await sync_service.sync_delete_image(image_url)

        if success:
            return {
                "message": f"Image {image_url} deleted successfully",
                "success": True,
            }
        else:
            return {"message": f"Image {image_url} not found", "success": False}

    except Exception as e:
        logger.error(f"Error deleting image {image_url}: {e}")
        return {"message": f"Error deleting image: {str(e)}", "success": False}


@sync_router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Check sync service status",
    description="Verify connection to dating app and face processing readiness",
)
async def check_sync_status(sync_service: SyncService = Depends(get_sync_service)):
    """
    Check sync service status

    Returns:
    - Dating app API connection status
    - Face processing service readiness
    """
    try:
        # Check dating app connection
        dating_app_connected = await sync_service.dating_app_client.verify_connection()

        # Check face processor
        face_processor_ready = sync_service.face_processor.device is not None

        return {
            "status": (
                "healthy"
                if (dating_app_connected and face_processor_ready)
                else "degraded"
            ),
            "dating_app_connected": dating_app_connected,
            "face_processor_ready": face_processor_ready,
            "face_processor_device": str(sync_service.face_processor.device),
            "min_face_confidence": sync_service.face_processor.min_confidence,
        }

    except Exception as e:
        logger.error(f"Error checking sync status: {e}")
        return {"status": "error", "error": str(e)}

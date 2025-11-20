from datetime import datetime
import logging
from fastapi import APIRouter, Body, Depends, status
from dependency_injector.wiring import inject

from ..core.dependency import get_sync_orchestrator
from app.schemas.sync import SyncRequest, SyncResponse, SyncSummary
from app.services.orchestrators.sync_orchestrator import SyncOrchestrator

logger = logging.getLogger(__name__)

sync_router = APIRouter(prefix="/sync", tags=["sync"])


@sync_router.post(
    "/users",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync users from dating app",
)
@inject
async def sync_users(
    sync_request: SyncRequest = Body(
        default=SyncRequest(limit=1000, force_resync=False, min_face_confidence=0.9)
    ),
    sync_orchestrator: SyncOrchestrator = Depends(get_sync_orchestrator),
):
    """
    Sync users from dating app to AI engine

    - **limit**: Optional limit on number of users to sync (1-1000)
    - **force_resync**: Force resync existing users (default: False)
    - **min_face_confidence**: Minimum face confidence threshold (0.0-1.0)
    """
    try:
        logger.info(
            "Starting sync",
            extra={
                "limit": sync_request.limit,
                "force_resync": sync_request.force_resync,
                "min_confidence": sync_request.min_face_confidence,
            },
        )

        summary = await sync_orchestrator.sync_users_from_dating_app(sync_request)

        response = SyncResponse(
            message=f"Sync completed: {summary.users_synced}/{summary.total_users_pulled} users synced",
            summary=summary,
        )

        logger.info(
            "Sync completed successfully",
            extra={
                "users_synced": summary.users_synced,
                "total_users": summary.total_users_pulled,
                "duration": summary.total_duration_seconds,
            },
        )

        return response

    except Exception as e:
        logger.error(
            "Error in sync endpoint",
            exc_info=True,
            extra={"sync_request": sync_request.dict()},
        )

        error_summary = SyncSummary(
            sync_timestamp=datetime.now(),
            errors=[
                {"error": f"Sync endpoint error: {str(e)}", "timestamp": datetime.now()}
            ],
        )

        return SyncResponse(message=f"Sync failed: {str(e)}", summary=error_summary)


import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.schemas.pool_image import ImportSummary, PhaseImagesResponse, PoolImageResponse
from ..services.import_service import ImportService
from app.services.pool_image_service import PoolImageService
from app.services.face_processing_service import FaceProcessingService

logger = logging.getLogger(__name__)

pool_image_router = APIRouter(prefix="/pool-images", tags=["pool-images"])


@pool_image_router.post(
    "/import",
    response_model=ImportSummary,
    status_code=status.HTTP_200_OK,
    summary="Import pool images from local dataset",
)
def import_pool_images(db: Session = Depends(get_db)):
    """
    Import pool images from local dataset (round1, round2, round3)

    This endpoint processes all images from the local dataset folder structure:
    - dataset/ALL/ALL/round1/ → Phase 1 images
    - dataset/ALL/ALL/round2/ → Phase 2 images
    - dataset/ALL/ALL/round3/ → Phase 3 images
    """
    try:
        logger.info("Starting pool images import")

        dataset_path = getattr(settings, "DATASET_PATH", "../dataset/ALL/ALL")

        face_processor = FaceProcessingService(
            min_confidence=settings.MIN_FACE_CONFIDENCE
        )

        importer = ImportService(
            db=db,
            face_processor=face_processor,
            dataset_base_path=dataset_path,
        )

        summary = importer.import_all_rounds()

        # Calculate totals
        total_success = (
            summary["round1"]["success"]
            + summary["round2"]["success"]
            + summary["round3"]["success"]
        )

        total_failed = (
            summary["round1"]["failed"]
            + summary["round2"]["failed"]
            + summary["round3"]["failed"]
        )

        message = f"Import completed: {total_success} images imported successfully"
        if total_failed > 0:
            message += f", {total_failed} failed"

        return ImportSummary(
            message=message,
            round1=summary["round1"],
            round2=summary["round2"],
            round3=summary["round3"],
            errors=summary["errors"],
        )

    except Exception as e:
        logger.error("Error during pool images import", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


@pool_image_router.get(
    "/phase/{phase}",
    response_model=PhaseImagesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get images for a specific phase",
)
def get_phase_images(phase: int, db: Session = Depends(get_db)):
    """
    Get all images for a specific phase

    Args:
        phase: Phase number (1, 2, or 3)
    """
    if phase not in [1, 2, 3]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phase must be 1, 2, or 3",
        )

    try:
        images = PoolImageService.get_images_by_phase(db, phase)

        return PhaseImagesResponse(
            phase=phase,
            total_images=len(images),
            images=[PoolImageResponse.model_validate(img) for img in images],
        )

    except Exception as e:
        logger.error(f"Error fetching phase {phase} images", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch images: {str(e)}",
        )

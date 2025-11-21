import logging
import time
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.sync import ImageProcessingResult
from app.services.dating_app_client import DatingAppClient
from app.services.face_processing_service import FaceProcessingService
from app.services.user_image_service import UserImageService

logger = logging.getLogger(__name__)


class ImageSyncService:
    """Service for processing user images during sync"""

    def __init__(
        self,
        db: Session,
        dating_app_client: DatingAppClient | None = None,
        face_processor: FaceProcessingService | None = None,
    ):
        self.db = db
        self.dating_app_client = dating_app_client or DatingAppClient(
            base_url=settings.DATING_APP_BASE_URL or "",
            image_base_url=settings.DATING_APP_IMAGE_BASE_URL or "",
            api_key=settings.DATING_APP_API_KEY,
            timeout=settings.DATING_APP_TIMEOUT,
        )
        self.face_processor = (
            face_processor
            or FaceProcessingService(min_confidence=settings.MIN_FACE_CONFIDENCE)
        )

    async def process_user_image(
        self, user_id: UUID, image_path: str, min_face_confidence: float
    ) -> ImageProcessingResult:
        """
        Process a single user image

        Args:
            user_id: User UUID
            image_path: Image path from dating app
            min_face_confidence: Minimum face confidence threshold

        Returns:
            ImageProcessingResult with processing details
        """
        start_time = time.time()
        
        # Extract filename from path
        filename = self._extract_filename(image_path)

        result = ImageProcessingResult(
            image_url=filename,
            success=False,
            face_detected=False,
        )

        try:
            # Download image
            image = await self._download_image(image_path, result)
            if image is None:
                return result

            success, embedding, confidence, attributes = self._process_face(
                image, result
            )
            if not success:
                return result

            if not self._validate_quality(confidence, embedding, result):
                return result

            # Save to database
            self._save_to_database(user_id, filename, embedding, confidence, attributes)

            result.success = True
            result.face_detected = True
            result.face_confidence = confidence
            result.processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Successfully processed image {filename}",
                extra={
                    "user_id": str(user_id),
                    "confidence": confidence,
                    "processing_time_ms": result.processing_time_ms,
                },
            )

            return result

        except Exception as e:
            logger.error(
                f"Error processing image {image_path}: {e}",
                exc_info=True,
                extra={"user_id": str(user_id), "image_path": image_path},
            )
            result.error_message = str(e)
            return result

    def _extract_filename(self, image_path: str) -> str:
        """Extract filename from path"""
        return image_path.split("/")[-1]

    async def _download_image(self, image_path: str, result: ImageProcessingResult):
        """Download image from dating app"""
        image = await self.dating_app_client.download_image(image_path)

        if image is None:
            result.error_message = "Failed to download image"
            logger.warning(
                f"Failed to download image: {image_path}",
                extra={"image_path": image_path},
            )
            return None

        return image

    def _process_face(self, image, result: ImageProcessingResult):
        """Process image with face detection"""
        success, embedding, confidence, attributes = self.face_processor.process_image(
            image
        )

        if not success or embedding is None:
            result.face_detected = False
            result.face_confidence = confidence
            result.error_message = "No face detected or processing failed"
            logger.debug(
                f"No valid face in {result.image_url}",
                extra={"image_url": result.image_url},
            )
            return False, None, confidence, None

        return True, embedding, confidence, attributes

    def _validate_quality(
        self, confidence: float, embedding, result: ImageProcessingResult
    ) -> bool:
        """Validate face quality"""
        is_valid, error_msg = self.face_processor.validate_face_quality(
            confidence, embedding
        )

        if not is_valid:
            result.error_message = error_msg
            result.face_confidence = confidence
            logger.debug(
                f"Face quality check failed for {result.image_url}",
                extra={"image_url": result.image_url, "error": error_msg},
            )
            return False

        return True

    def _save_to_database(
        self,
        user_id: UUID,
        filename: str,
        embedding,
        confidence: float,
        attributes: dict,
    ):
        """Save processed image to database"""
        UserImageService.create_user_image(
            db=self.db,
            user_id=user_id,
            image_url=filename,
            face_embedding=embedding,
            face_confidence=confidence,
            facial_attributes=attributes,
            is_primary=False,
        )

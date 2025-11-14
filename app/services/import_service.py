import logging
import os
from PIL import Image
from sqlalchemy.orm import Session

from app.services.pool_image_service import PoolImageService
from app.services.face_processing_service import FaceProcessingService

logger = logging.getLogger(__name__)


class ImportService:
    """Service for importing pool images from local dataset"""

    def __init__(
        self,
        db: Session,
        face_processor: FaceProcessingService,
        dataset_base_path: str,
    ):
        self.db = db
        self.face_processor = face_processor
        self.dataset_base_path = dataset_base_path

    def import_all_rounds(self) -> dict:
        """
        Import all 3 rounds from local dataset

        Returns:
            Summary dict with import statistics
        """
        summary = {
            "round1": {"total": 0, "success": 0, "failed": 0, "skipped": 0},
            "round2": {"total": 0, "success": 0, "failed": 0, "skipped": 0},
            "round3": {"total": 0, "success": 0, "failed": 0, "skipped": 0},
            "errors": [],
        }

        logger.info("Starting pool images import from local dataset")

        for phase in [1, 2, 3]:
            round_name = f"round{phase}"
            folder_path = os.path.join(self.dataset_base_path, round_name)

            if not os.path.exists(folder_path):
                logger.warning(f"Folder {folder_path} does not exist, skipping")
                summary["errors"].append(
                    {"phase": phase, "error": f"Folder {round_name} not found"}
                )
                continue

            logger.info(f"Processing {round_name} from {folder_path}")
            round_summary = self._import_round(folder_path, phase)

            summary[round_name] = round_summary

        logger.info("Import completed", extra={"summary": summary})
        return summary

    def _import_round(self, folder_path: str, phase: int) -> dict:
        """
        Import images from a specific round folder

        Args:
            folder_path: Path to round folder
            phase: Phase number (1, 2, 3)

        Returns:
            Summary dict for this round
        """
        summary = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

        # Get all image files
        image_files = [
            f
            for f in os.listdir(folder_path)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]

        summary["total"] = len(image_files)
        logger.info(f"Found {len(image_files)} images in round{phase}")

        for image_file in image_files:
            try:
                image_path = os.path.join(folder_path, image_file)

                if PoolImageService.get_pool_image_by_url(self.db, image_file):

                    logger.debug(f"Image {image_file} already exists, skipping")
                    summary["skipped"] += 1
                    continue

                success = self._import_single_image(image_path, image_file, phase)

                if success:
                    summary["success"] += 1
                else:
                    summary["failed"] += 1

            except Exception as e:
                logger.error(f"Error importing {image_file}: {e}", exc_info=True)
                summary["failed"] += 1

        self.db.commit()

        logger.info(
            f"Round{phase} import completed",
            extra={
                "phase": phase,
                "success": summary["success"],
                "failed": summary["failed"],
                "skipped": summary["skipped"],
            },
        )

        return summary

    def _import_single_image(
        self, image_path: str, image_file: str, phase: int
    ) -> bool:
        """
        Import a single image

        Args:
            image_path: Full path to image file
            image_file: Image filename
            phase: Phase number

        Returns:
            True if successful
        """
        try:
            # Extract person code from filename
            person_code = self._extract_person_code(image_file)

            # Load image
            image = Image.open(image_path).convert("RGB")

            # Process face
            success, embedding, confidence, attributes = (
                self.face_processor.process_image(image)
            )

            if not success or embedding is None:
                logger.warning(
                    f"No valid face detected in {image_file}",
                    extra={"image_file": image_file, "confidence": confidence},
                )
                return False

            # Validate face quality
            is_valid, error_msg = self.face_processor.validate_face_quality(
                confidence, embedding
            )

            if not is_valid:
                logger.warning(
                    f"Face quality check failed for {image_file}: {error_msg}",
                    extra={"image_file": image_file, "confidence": confidence},
                )
                return False
            image_url = f"/round{phase}/{image_file}"

            # Create pool image
            PoolImageService.create_pool_image(
                db=self.db,
                image_url=image_url,
                person_code=person_code,
                face_embedding=embedding,
                face_confidence=confidence,
                facial_attributes=attributes,
                phase=phase,
            )

            logger.info(
                f"Successfully imported {image_file}",
                extra={
                    "image_file": image_file,
                    "person_code": person_code,
                    "phase": phase,
                    "confidence": confidence,
                },
            )

            return True

        except Exception as e:
            logger.error(f"Error importing {image_file}: {e}", exc_info=True)
            return False

    @staticmethod
    def _extract_person_code(filename: str) -> str:
        """
        Extract person code from filename

        Args:
            filename: Image filename (e.g., "00001.png")

        Returns:
            Person code (e.g., "P00001")
        """

        name = filename.split(".")[0]
        return f"P{name}"

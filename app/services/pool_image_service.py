import logging
from typing import Optional
from uuid import UUID

import numpy as np
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.pool_image import PoolImage

logger = logging.getLogger(__name__)


class PoolImageService:
    """Service for managing pool images"""

    def __init__(self, db: Session):
        self.db = db
        
    @staticmethod
    def create_pool_image(
        db: Session,
        image_url: str,
        person_code: str,
        face_embedding: np.ndarray,
        face_confidence: float,
        facial_attributes: dict,
        phase: int,
    ) -> PoolImage:
        """
        Create a new pool image from local dataset

        Args:
            db: Database session
            image_url: Image filename/path
            person_code: Person identifier from filename
            face_embedding: Face embedding vector (512-dim)
            face_confidence: Face detection confidence
            facial_attributes: Facial attributes dict
            phase: Phase number (1, 2, or 3) from folder name

        Returns:
            Created PoolImage instance
        """
        try:
            embedding_list = (
                face_embedding.tolist()
                if isinstance(face_embedding, np.ndarray)
                else face_embedding
            )

            pool_image = PoolImage(
                image_URL=image_url,
                person_code=person_code,
                face_embedding=embedding_list,
                face_confidence=face_confidence,
                facial_attributes=facial_attributes,
                phase_eligibility=[phase],
                is_active=True,
            )

            db.add(pool_image)
            db.flush()
            db.refresh(pool_image)

            logger.info(f"Created pool image {pool_image.id} for person {person_code}")

            return pool_image

        except SQLAlchemyError as e:
            logger.error(f"Database error creating pool image: {e}", exc_info=True)
            db.rollback()
            raise

    @staticmethod
    def get_pool_image_by_url(db: Session, image_url: str) -> Optional[PoolImage]:
        """Check if image already exists"""
        try:
            return db.query(PoolImage).filter(PoolImage.image_URL == image_url).first()
        except Exception as e:
            logger.error(f"Error fetching pool image by URL: {e}")
            return None

    def get_images_by_phase(self, phase: int) -> list[PoolImage]:
        """
        Get all images for a specific phase

        Args:
            db: Database session
            phase: Phase number (1, 2, 3)

        Returns:
            List of PoolImage objects
        """
        try:
            images = (
                self.db.query(PoolImage)
                .filter(
                    PoolImage.is_active == True,
                    PoolImage.phase_eligibility.any(phase) 
                )
                .all()
            )

            logger.info(f"Retrieved {len(images)} images for phase {phase}")
            return images

        except Exception as e:
            logger.error(f"Error fetching images for phase {phase}: {e}")
            return []

    def update_usage_statistics(
        self,
        image_id: UUID,
        action: str,
    ) -> bool:
        """
        Update statistics when user makes a choice

        Args:
            db: Database session
            image_id: Pool image UUID
            action: User action (LIKE, PASS, PREFER)

        Returns:
            True if successful
        """
        try:
            pool_image = self.db.query(PoolImage).filter(PoolImage.id == image_id).first()

            if not pool_image:
                logger.warning(f"Pool image {image_id} not found")
                return False

            pool_image.usage_count = (pool_image.usage_count or 0) + 1

            if action == "LIKE":
                pool_image.like_count = (pool_image.like_count or 0) + 1
            elif action == "PASS":
                pool_image.pass_count = (pool_image.pass_count or 0) + 1
            elif action == "PREFER":
                pool_image.prefer_count = (pool_image.prefer_count or 0) + 1

            self.db.commit()
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error updating statistics: {e}")
            self.db.rollback()
            return False

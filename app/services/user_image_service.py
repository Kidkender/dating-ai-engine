import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import numpy as np

from app.models.user_image import UserImage, ImageStatus

logger = logging.getLogger(__name__)


class UserImageService:
    """Service for managing user images"""

    @staticmethod
    def create_user_image(
        db: Session,
        user_id: UUID,
        image_url: str,
        face_embedding: np.ndarray,  # type: ignore
        face_confidence: float,
        facial_attributes: dict,  # type: ignore
        is_primary: bool = False,
    ) -> UserImage:
        """
        Create a new user image record

        Args:
            db: Database session
            user_id: User UUID
            image_url: Image URL/filename
            face_embedding: Face embedding vector (512-dim)
            face_confidence: Face detection confidence
            facial_attributes: Facial attributes dict
            is_primary: Whether this is the primary image

        Returns:
            Created UserImage instance
        """
        try:
            # Convert numpy array to list for pgvector
            embedding_list = (
                face_embedding.tolist()
                if isinstance(face_embedding, np.ndarray)  # type: ignore
                else face_embedding
            )

            user_image = UserImage(
                user_id=user_id,
                image_URL=image_url,
                face_embedding=embedding_list,
                face_confidence=face_confidence,
                facial_attributes=facial_attributes,
                is_primary=is_primary,
                processing_status=ImageStatus.COMPLETED,
            )

            db.add(user_image)
            db.flush()
            db.refresh(user_image)

            logger.info(f"Created user image {user_image.id} for user {user_id}")
            return user_image

        except SQLAlchemyError as e:
            logger.error(f"Database error creating user image: {e}")
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Error creating user image: {e}")
            raise

    @staticmethod
    def get_user_images_count(db: Session, user_id: UUID) -> int:
        """
        Get count of valid images for a user

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Count of images
        """
        try:
            count = (
                db.query(UserImage)
                .filter(
                    UserImage.user_id == user_id,
                    UserImage.processing_status == ImageStatus.COMPLETED,
                )
                .count()
            )
            return count
        except Exception as e:
            logger.error(f"Error counting user images: {e}")
            return 0

    @staticmethod
    def get_user_images(db: Session, user_id: UUID) -> list[UserImage]:
        """
        Get all images for a user

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            List of UserImage objects
        """
        try:
            return db.query(UserImage).filter(UserImage.user_id == user_id).all()
        except Exception as e:
            logger.error(f"Error fetching user images: {e}")
            return []

    @staticmethod
    def set_primary_image(db: Session, user_id: UUID, image_id: UUID) -> bool:
        """
        Set an image as primary for a user

        Args:
            db: Database session
            user_id: User UUID
            image_id: Image UUID to set as primary

        Returns:
            True if successful
        """
        try:
            # Unset all primary flags for this user
            db.query(UserImage).filter(UserImage.user_id == user_id).update(
                {"is_primary": False}
            )

            # Set the specified image as primary
            result = (
                db.query(UserImage)
                .filter(UserImage.id == image_id, UserImage.user_id == user_id)
                .update({"is_primary": True})
            )

            db.commit()

            if result == 0:
                logger.warning(f"Image {image_id} not found for user {user_id}")
                return False

            logger.info(f"Set image {image_id} as primary for user {user_id}")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Database error setting primary image: {e}")
            db.rollback()
            return False

    @staticmethod
    def set_primary_by_highest_confidence(db: Session, user_id: UUID) -> bool:
        """
        Set the image with highest confidence as primary

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            True if successful
        """
        try:
            # Find image with highest confidence
            highest_conf_image = (
                db.query(UserImage)
                .filter(
                    UserImage.user_id == user_id,
                    UserImage.processing_status == ImageStatus.COMPLETED,
                )
                .order_by(UserImage.face_confidence.desc())  # type: ignore
                .first()
            )

            if not highest_conf_image:
                logger.warning(f"No completed images found for user {user_id}")
                return False

            return UserImageService.set_primary_image(
                db, user_id, highest_conf_image.id  # type: ignore
            )

        except Exception as e:
            logger.error(f"Error setting primary by confidence: {e}")
            return False

    @staticmethod
    def delete_user_image(db: Session, image_url: str) -> bool:
        """
        Delete a user image by URL

        Args:
            db: Database session
            image_url: Image URL/filename

        Returns:
            True if deleted successfully
        """
        try:
            result = (
                db.query(UserImage).filter(UserImage.image_URL == image_url).delete()
            )

            db.commit()

            if result > 0:
                logger.info(f"Deleted user image: {image_url}")
                return True
            else:
                logger.warning(f"Image not found: {image_url}")
                return False

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting image: {e}")
            db.rollback()
            return False

    @staticmethod
    def check_and_update_user_primary(db: Session, user_id: UUID) -> None:
        """
        Check if user has any images, and update primary if needed

        Args:
            db: Database session
            user_id: User UUID
        """
        try:
            images = UserImageService.get_user_images(db, user_id)

            if not images:
                logger.info(f"User {user_id} has no images")
                return

            # Check if any image is primary
            has_primary = any(img.is_primary for img in images)

            if not has_primary:
                # Set highest confidence as primary
                UserImageService.set_primary_by_highest_confidence(db, user_id)
                logger.info(f"Set new primary image for user {user_id}")

        except Exception as e:
            logger.error(f"Error checking/updating primary: {e}")

    @staticmethod
    def get_primary_image(db: Session, user_id: UUID) -> Optional[UserImage]:
        """
        Get primary image for a user

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Primary UserImage or None
        """
        try:
            return (
                db.query(UserImage)
                .filter(UserImage.user_id == user_id, UserImage.is_primary == True)
                .first()
            )
        except Exception as e:
            logger.error(f"Error fetching primary image: {e}")
            return None

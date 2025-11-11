import logging
from datetime import datetime
import time
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User, UserStatus
from app.schemas.sync import (
    DatingAppUser,
    ImageProcessingResult,
    UserSyncResult,
    SyncSummary,
    SyncRequest,
)
from app.services.dating_app_client import DatingAppClient
from app.services.face_processing_service import FaceProcessingService
from app.services.user_image_service import UserImageService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class SyncService:
    """Main service for syncing users from dating app"""

    def __init__(
        self,
        dating_app_client: DatingAppClient,
        face_processor: FaceProcessingService,
        db: Session,
    ):
        """
        Initialize sync service

        Args:
            dating_app_client: Client for dating app API
            face_processor: Face processing service
            db: Database session
        """
        self.dating_app_client = dating_app_client
        self.face_processor = face_processor
        self.db = db

    async def sync_users_from_dating_app(
        self, sync_request: SyncRequest
    ) -> SyncSummary:
        """
        Main entry point for syncing users from dating app

        Args:
            sync_request: Sync configuration

        Returns:
            SyncSummary with results
        """
        start_time = time.time()
        summary = SyncSummary(sync_timestamp=datetime.now())

        try:
            logger.info("Starting user sync from dating app")

            # Verify connection
            if not await self.dating_app_client.verify_connection():
                summary.errors.append(
                    {
                        "error": "Failed to connect to dating app API",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return summary

            # Fetch users from dating app
            dating_app_users = await self.dating_app_client.fetch_all_users(
                limit=sync_request.limit
            )
            summary.total_users_pulled = len(dating_app_users)

            logger.info(f"Fetched {len(dating_app_users)} users from dating app")

            # Process each user
            user_results = []
            for dating_user in dating_app_users:
                try:
                    result = await self.sync_single_user(
                        dating_user,
                        sync_request.force_resync,
                        sync_request.min_face_confidence,
                    )
                    user_results.append(result)

                    # Update summary
                    if result.success:
                        summary.users_synced += 1
                        summary.total_images_processed += result.images_processed
                        summary.faces_detected += result.images_with_faces

                        if result.is_active:
                            summary.users_with_valid_faces += 1
                        else:
                            summary.users_without_faces += 1
                    else:
                        summary.users_skipped += 1
                        summary.errors.append(
                            {
                                "email": result.email,
                                "error": result.error_message,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )

                except Exception as e:
                    logger.error(f"Error syncing user {dating_user.email}: {e}")
                    summary.users_skipped += 1
                    summary.errors.append(
                        {
                            "email": dating_user.email,
                            "error": str(e),
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

            # Calculate statistics
            summary.faces_failed = (
                summary.total_images_processed - summary.faces_detected
            )

            if summary.faces_detected > 0:
                total_confidence = sum(
                    img_result.face_confidence or 0
                    for user_result in user_results
                    for img_result in user_result.image_results
                    if img_result.face_confidence is not None
                )
                summary.avg_confidence = total_confidence / summary.faces_detected

            summary.total_duration_seconds = time.time() - start_time

            logger.info(
                f"Sync completed: {summary.users_synced}/{summary.total_users_pulled} users synced"
            )
            return summary

        except Exception as e:
            logger.error(f"Error during sync: {e}")
            summary.errors.append(
                {
                    "error": f"Sync failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            )
            summary.total_duration_seconds = time.time() - start_time
            return summary

    async def sync_single_user(
        self,
        dating_user: DatingAppUser,
        force_resync: bool = False,
        min_face_confidence: float = 0.80,
    ) -> UserSyncResult:
        """
        Sync a single user from dating app

        Args:
            dating_user: User data from dating app
            force_resync: Force resync even if user exists
            min_face_confidence: Minimum face confidence threshold

        Returns:
            UserSyncResult
        """
        result = UserSyncResult(email=dating_user.email, success=False)

        try:
            # Check if user already exists
            existing_user = (
                self.db.query(User).filter(User.email == dating_user.email).first()
            )

            if existing_user and not force_resync:
                logger.info(f"User {dating_user.email} already exists, skipping")
                result.error_message = "User already exists"
                return result

            # Create or get user
            if existing_user:
                db_user = existing_user
                logger.info(f"Force resyncing user {dating_user.email}")
            else:
                db_user = await self._create_user(dating_user)

            result.user_id = db_user.id

            # Process images
            if not dating_user.images:  # Use images property
                logger.warning(f"User {dating_user.email} has no images")
                result.error_message = "No images to process"
                result.success = True
                return result

            # Process each image
            image_results = []
            for image_path in dating_user.images:  # Use images property
                img_result = await self._process_user_image(
                    db_user.id, image_path, min_face_confidence
                )
                image_results.append(img_result)

                if img_result.success and img_result.face_detected:
                    result.images_with_faces += 1

                result.images_processed += 1

            result.image_results = image_results

            # Update user status based on results
            if result.images_with_faces > 0:
                db_user.status = UserStatus.ACTIVE
                result.is_active = True

                # Set primary image (highest confidence)
                UserImageService.set_primary_by_highest_confidence(self.db, db_user.id)

                logger.info(
                    f"User {dating_user.email} has {result.images_with_faces} valid faces, status: ACTIVE"
                )
            else:
                db_user.status = UserStatus.ONBOARDING
                result.is_active = False
                logger.warning(
                    f"User {dating_user.email} has no valid faces, status: ONBOARDING"
                )

            self.db.commit()
            result.success = True

            return result

        except Exception as e:
            logger.error(f"Error syncing user {dating_user.email}: {e}")
            self.db.rollback()
            result.error_message = str(e)
            return result

    async def _create_user(self, dating_user: DatingAppUser) -> User:
        """
        Create a new user in database

        Args:
            dating_user: User data from dating app

        Returns:
            Created User instance
        """
        try:
            session_token = UserService.generate_session_token()

            # Map gender using property
            gender = None
            if dating_user.gender:
                from app.models.user import Gender

                gender_upper = dating_user.gender  # Already uppercase from property
                if gender_upper in [g.value for g in Gender]:
                    gender = Gender[gender_upper]

            # Use properties for name and email
            db_user = User(
                email=dating_user.email,  # Property
                name=dating_user.name,  # Property (fullName or userName + userSurname)
                gender=gender,
                session_token=session_token,
                status=UserStatus.ONBOARDING,
            )

            self.db.add(db_user)
            self.db.flush()
            self.db.refresh(db_user)

            logger.info(f"Created user {db_user.id} for {dating_user.email}")
            return db_user

        except SQLAlchemyError as e:
            logger.error(f"Database error creating user: {e}")
            self.db.rollback()
            raise

    async def _process_user_image(
        self, user_id: UUID, image_path: str, min_face_confidence: float
    ) -> ImageProcessingResult:
        """
        Process a single user image

        Args:
            user_id: User UUID
            image_path: Image path from dating app (e.g., "images/1746613443481_1000003282.png")
            min_face_confidence: Minimum face confidence

        Returns:
            ImageProcessingResult
        """
        start_time = time.time()

        # Extract filename from path for storage
        # "images/1746613443481_1000003282.png" -> "1746613443481_1000003282.png"
        filename = image_path.split("/")[-1]

        result = ImageProcessingResult(
            image_url=filename,  # Store just the filename
            success=False,
            face_detected=False,
        )

        try:
            # Download image using full path
            image = await self.dating_app_client.download_image(image_path)
            if image is None:
                result.error_message = "Failed to download image"
                logger.warning(f"Failed to download image: {image_path}")
                return result

            # Process image with face detection
            success, embedding, confidence, attributes = (
                self.face_processor.process_image(image)
            )

            if not success or embedding is None:
                result.face_detected = False
                result.face_confidence = confidence
                result.error_message = "No face detected or processing failed"
                logger.debug(f"No valid face in {filename}")
                return result

            # Validate face quality
            is_valid, error_msg = self.face_processor.validate_face_quality(
                confidence, embedding
            )
            if not is_valid:
                result.error_message = error_msg
                result.face_confidence = confidence
                logger.debug(f"Face quality check failed for {filename}: {error_msg}")
                return result

            # Save to database with filename only
            user_image = UserImageService.create_user_image(
                db=self.db,
                user_id=user_id,
                image_url=filename,  # Store just filename
                face_embedding=embedding,
                face_confidence=confidence,
                facial_attributes=attributes,
                is_primary=False,  # Will be set later based on confidence
            )

            result.success = True
            result.face_detected = True
            result.face_confidence = confidence
            result.processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Successfully processed image {filename} with confidence {confidence:.3f}"
            )
            return result

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            result.error_message = str(e)
            return result

    async def sync_delete_image(self, image_url: str) -> bool:
        """
        Handle image deletion from dating app

        Args:
            image_url: Image URL to delete

        Returns:
            True if successful
        """
        try:
            # Get the user_id before deletion
            from app.models.user_image import UserImage

            user_image = (
                self.db.query(UserImage)
                .filter(UserImage.image_URL == image_url)
                .first()
            )

            if not user_image:
                logger.warning(f"Image {image_url} not found for deletion")
                return False

            user_id = user_image.user_id
            was_primary = user_image.is_primary

            # Delete the image
            deleted = UserImageService.delete_user_image(self.db, image_url)

            if deleted:
                # Check remaining images
                remaining_count = UserImageService.get_user_images_count(
                    self.db, user_id
                )

                # Update user status
                user = self.db.query(User).filter(User.id == user_id).first()
                if user:
                    if remaining_count == 0:
                        user.status = UserStatus.ONBOARDING
                        logger.info(
                            f"User {user_id} has no images left, status -> ONBOARDING"
                        )
                    elif was_primary:
                        # Set new primary if the deleted one was primary
                        UserImageService.set_primary_by_highest_confidence(
                            self.db, user_id
                        )
                        logger.info(f"Set new primary image for user {user_id}")

                    self.db.commit()

                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting image {image_url}: {e}")
            self.db.rollback()
            return False

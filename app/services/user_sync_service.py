import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User, UserStatus, Gender
from app.schemas.sync import DatingAppUser, UserSyncResult
from app.services.user_service import UserService
from app.services.image_sync_service import ImageSyncService
from app.services.user_image_service import UserImageService

logger = logging.getLogger(__name__)


class UserSyncService:
    """Service for syncing individual users from dating app"""

    def __init__(
        self,
        db: Session,
        image_sync_service: ImageSyncService,
    ):
        self.db = db
        self.image_sync_service = image_sync_service

    async def sync_single_user(
        self,
        dating_user: DatingAppUser,
        force_resync: bool = False,
        min_face_confidence: float = 0.90,
    ) -> UserSyncResult:
        """
        Sync a single user from dating app

        Args:
            dating_user: User data from dating app
            force_resync: Force resync even if user exists
            min_face_confidence: Minimum face confidence threshold

        Returns:
            UserSyncResult with sync details
        """
        result = UserSyncResult(email=dating_user.email, success=False)

        try:
            # Get or create user
            db_user = await self._get_or_create_user(dating_user, force_resync, result)

            if db_user is None:
                return result

            result.user_id = db_user.id

            # Process user images
            await self._process_user_images(
                db_user, dating_user, min_face_confidence, result
            )

            # Update user status based on results
            self._update_user_status(db_user, result)

            self.db.commit()
            result.success = True

            return result

        except Exception as e:
            logger.error(
                f"Error syncing user {dating_user.email}: {e}",
                exc_info=True,
                extra={"user_email": dating_user.email},
            )
            self.db.rollback()
            result.error_message = str(e)
            return result

    async def _get_or_create_user(
        self, dating_user: DatingAppUser, force_resync: bool, result: UserSyncResult
    ) -> User | None:
        """Get existing user or create new one"""
        existing_user = (
            self.db.query(User).filter(User.email == dating_user.email).first()
        )

        if existing_user and not force_resync:
            logger.info(
                f"User {dating_user.email} already exists, skipping",
                extra={"user_email": dating_user.email},
            )
            result.error_message = "User already exists"
            return None

        if existing_user:
            logger.info(
                f"Force resyncing user {dating_user.email}",
                extra={"user_email": dating_user.email},
            )
            return existing_user

        return self._create_user(dating_user)

    def _create_user(self, dating_user: DatingAppUser) -> User:
        """Create a new user in database"""
        try:
            session_token = UserService.generate_session_token()

            # Map gender
            gender = self._map_gender(dating_user.gender)

            db_user = User(
                email=dating_user.email,
                name=dating_user.name,
                gender=gender,
                session_token=session_token,
                status=UserStatus.ONBOARDING,
            )

            self.db.add(db_user)
            self.db.flush()
            self.db.refresh(db_user)

            logger.info(
                f"Created user {db_user.id} for {dating_user.email}",
                extra={"user_id": str(db_user.id), "user_email": dating_user.email},
            )
            return db_user

        except SQLAlchemyError as e:
            logger.error(
                f"Database error creating user: {e}",
                exc_info=True,
                extra={"user_email": dating_user.email},
            )
            self.db.rollback()
            raise

    def _map_gender(self, gender_str: str | None) -> Gender | None:
        """Map gender string to Gender enum"""
        if not gender_str:
            return None

        gender_upper = gender_str.upper()
        if gender_upper in [g.value for g in Gender]:
            return Gender[gender_upper]

        return None

    async def _process_user_images(
        self,
        db_user: User,
        dating_user: DatingAppUser,
        min_face_confidence: float,
        result: UserSyncResult,
    ):
        """Process all images for a user"""
        if not dating_user.images:
            logger.warning(
                f"User {dating_user.email} has no images",
                extra={"user_id": str(db_user.id), "user_email": dating_user.email},
            )
            result.error_message = "No images to process"
            return

        # Process each image
        for image_path in dating_user.images:
            img_result = await self.image_sync_service.process_user_image(
                user_id=db_user.id,
                image_path=image_path,
                min_face_confidence=min_face_confidence,
            )

            result.image_results.append(img_result)
            result.images_processed += 1

            if img_result.success and img_result.face_detected:
                result.images_with_faces += 1

    def _update_user_status(self, db_user: User, result: UserSyncResult):
        """Update user status based on image processing results"""
        if result.images_with_faces > 0:
            db_user.status = UserStatus.ACTIVE
            result.is_active = True

            # Set primary image (highest confidence)
            UserImageService.set_primary_by_highest_confidence(self.db, db_user.id)

            logger.info(
                f"User {db_user.email} has {result.images_with_faces} valid faces, status: ACTIVE",
                extra={
                    "user_id": str(db_user.id),
                    "faces_count": result.images_with_faces,
                },
            )
        else:
            db_user.status = UserStatus.ONBOARDING
            result.is_active = False

            logger.warning(
                f"User {db_user.email} has no valid faces, status: ONBOARDING",
                extra={"user_id": str(db_user.id)},
            )

import logging
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user_choice import UserChoice, ChoiceType
from app.models.user import User, UserStatus
from app.models.pool_image import PoolImage
from app.services.pool_image_service import PoolImageService
from app.core.exception import AppException

logger = logging.getLogger(__name__)


class UserChoiceService:
    """Service for managing user choices"""

    @staticmethod
    def create_choice(
        db: Session,
        user_id: UUID,
        pool_image_id: UUID,
        action: str,
        response_time_ms: Optional[int] = None,
    ) -> dict:
        """
        Create a new user choice

        Args:
            db: Database session
            user_id: User UUID
            pool_image_id: Pool image UUID
            action: User action (LIKE, PASS, PREFER)
            response_time_ms: Response time in milliseconds

        Returns:
            Dictionary with choice info and progress

        Raises:
            AppException: If validation fails
        """
        try:
            # Validate user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise AppException(
                    error_code="error.user.not-found",
                    message="User not found",
                    status_code=404,
                )

            if user.status != UserStatus.ACTIVE:
                raise AppException(
                    error_code="error.user.not-active",
                    message="User is not active",
                    status_code=400,
                )

            # Get current phase and position
            current_phase, position = UserChoiceService._get_current_phase_and_position(
                db, user_id
            )

            # Check if completed
            if current_phase == "COMPLETED":
                raise AppException(
                    error_code="error.choice.all-completed",
                    message="All phases completed",
                    status_code=400,
                )

            # Validate pool image
            pool_image = db.query(PoolImage).filter(PoolImage.id == pool_image_id).first()
            if not pool_image:
                raise AppException(
                    error_code="error.image.not-found",
                    message="Pool image not found",
                    status_code=404,
                )

            if not pool_image.is_active:
                raise AppException(
                    error_code="error.image.not-active",
                    message="Pool image is not active",
                    status_code=400,
                )

            # Validate image is for current phase
            if current_phase not in pool_image.phase_eligibility:
                raise AppException(
                    error_code="error.choice.invalid-phase",
                    message=f"This image is not available for phase {current_phase}",
                    status_code=400,
                )

            # Validate action
            try:
                choice_action = ChoiceType[action.upper()]
            except KeyError:
                raise AppException(
                    error_code="error.choice.invalid-action",
                    message=f"Invalid action: {action}. Must be LIKE, PASS, or PREFER",
                    status_code=400,
                )

            # Create choice
            user_choice = UserChoice(
                user_id=user_id,
                pool_image_id=pool_image_id,
                phase=current_phase,
                position_in_phase=position,
                action=choice_action,
                response_time_ms=response_time_ms,
            )

            db.add(user_choice)
            db.flush()

            # Update pool image statistics
            PoolImageService.update_usage_statistics(db, pool_image_id, action.upper())

            # Update user status if completed
            new_phase, new_position = UserChoiceService._get_current_phase_and_position(
                db, user_id
            )

            if new_phase == "COMPLETED":
                user.status = UserStatus.COMPLETED
                db.flush()

            db.commit()

            logger.info(
                f"Choice created for user {user_id}",
                extra={
                    "user_id": str(user_id),
                    "pool_image_id": str(pool_image_id),
                    "action": action,
                    "phase": current_phase,
                    "position": position,
                },
            )

            # Return progress
            return {
                "choice_id": str(user_choice.id),
                "current_phase": new_phase if new_phase != "COMPLETED" else current_phase,
                "phase_progress": f"{new_position - 1 if new_phase != 'COMPLETED' else 20}/20",
                "total_choices": UserChoiceService._count_user_choices(db, user_id),
                "all_completed": new_phase == "COMPLETED",
            }

        except IntegrityError as e:
            db.rollback()
            if "unique_user_pool_image" in str(e):
                raise AppException(
                    error_code="error.choice.already-exists",
                    message="You already voted for this image",
                    status_code=400,
                )
            raise

        except AppException:
            db.rollback()
            raise

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating choice: {e}", exc_info=True)
            raise

    @staticmethod
    def create_batch_choices(
        db: Session,
        user_id: UUID,
        choices_data: list[dict],
    ) -> dict:
        """
        Create multiple choices at once (batch operation)

        Args:
            db: Database session
            user_id: User UUID
            choices_data: List of choice dictionaries containing:
                - pool_image_id: UUID
                - action: str (LIKE, PASS, PREFER)
                - response_time_ms: Optional[int]

        Returns:
            Dictionary with batch results and progress

        Raises:
            AppException: If validation fails
        """
        try:
            if len(choices_data) != 20:
                raise AppException(
                    error_code="error.choice.invalid-count",
                    message=f"Must submit exactly 20 choices for a phase, received {len(choices_data)}",
                    status_code=400,
                )
              
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise AppException(
                    error_code="error.user.not-found",
                    message="User not found",
                    status_code=404,
                )

            if user.status != UserStatus.ACTIVE:
                raise AppException(
                    error_code="error.user.not-active",
                    message="User is not active",
                    status_code=400,
                )

            # Get current phase
            current_phase, start_position = UserChoiceService._get_current_phase_and_position(
                db, user_id
            )

            if current_phase == "COMPLETED":
                raise AppException(
                    error_code="error.choice.all-completed",
                    message="All phases completed",
                    status_code=400,
                )

            current_phase_count = db.query(UserChoice).filter(
                UserChoice.user_id == user_id,
                UserChoice.phase == current_phase
            ).count()
            
            if current_phase_count > 0:
                logger.warning(
                    f"User {user_id} has {current_phase_count} choices in phase {current_phase}. Deleting to redo phase.",
                    extra={"user_id": str(user_id), "phase": current_phase}
                )
                
                db.query(UserChoice).filter(
                    UserChoice.user_id == user_id,
                    UserChoice.phase == current_phase
                ).delete()
                db.flush()
                
                start_position = 1
                
            pool_image_ids = [choice["pool_image_id"] for choice in choices_data]
            
            if len(pool_image_ids) != len(set(pool_image_ids)):
                raise AppException(
                    error_code="error.choice.duplicate-images",
                    message="Cannot vote for the same image multiple times in one submission",
                    status_code=400,
                )
            pool_images = db.query(PoolImage).filter(
                        PoolImage.id.in_(pool_image_ids),
                        PoolImage.is_active == True
                    ).all()

            if len(pool_images) != 20:
                raise AppException(
                    error_code="error.choice.invalid-images",
                    message=f"Found {len(pool_images)} valid images, need exactly 20 active images",
                    status_code=400,
                )
            
            pool_images_dict = {img.id: img for img in pool_images}

            invalid_images = []
            for img_id in pool_image_ids:
                img = pool_images_dict.get(img_id)
                if not img:
                    invalid_images.append(str(img_id))
                elif current_phase not in img.phase_eligibility:
                    invalid_images.append(f"{img_id} (not eligible for phase {current_phase})")

            if invalid_images:
                raise AppException(
                    error_code="error.choice.invalid-phase-images",
                    message=f"Some images are not eligible for phase {current_phase}",
                    status_code=400,
                    details={"invalid_images": invalid_images}
                )
            # Check if user already voted for any of these images (in previous phases)
            existing_votes = db.query(UserChoice.pool_image_id).filter(
                UserChoice.user_id == user_id,
                UserChoice.pool_image_id.in_(pool_image_ids)
            ).all()

            if existing_votes:
                already_voted = [str(vote[0]) for vote in existing_votes]
                raise AppException(
                    error_code="error.choice.already-voted",
                    message=f"Already voted for {len(already_voted)} images in previous phases",
                    status_code=400,
                    details={"already_voted_images": already_voted}
                )

            # All validations passed - create all 20 choices
            created_choices = []
            for idx, choice_data in enumerate(choices_data):
                pool_image_id = choice_data["pool_image_id"]
                action = choice_data["action"]
                response_time_ms = choice_data.get("response_time_ms")

                # Validate action
                try:
                    choice_action = ChoiceType[action.upper()]
                except KeyError:
                    raise AppException(
                        error_code="error.choice.invalid-action",
                        message=f"Invalid action '{action}' at position {idx + 1}. Must be LIKE, PASS, or PREFER",
                        status_code=400,
                    )

                # Create choice
                position = start_position + idx
                user_choice = UserChoice(
                    user_id=user_id,
                    pool_image_id=pool_image_id,
                    phase=current_phase,
                    position_in_phase=position,
                    action=choice_action,
                    response_time_ms=response_time_ms,
                )

                db.add(user_choice)
                created_choices.append(user_choice)

                # Update pool image statistics
                PoolImageService.update_usage_statistics(
                    db, pool_image_id, action.upper()
                )

            db.flush()

            # Check if phase/all completed after batch
            new_phase, new_position = UserChoiceService._get_current_phase_and_position(
                db, user_id
            )

            # If completed all 3 phases, update user status
            if new_phase == "COMPLETED":
                user.status = UserStatus.COMPLETED
                db.flush()

            db.commit()

            logger.info(
                f"Successfully created 20 choices for user {user_id} phase {current_phase}",
                extra={
                    "user_id": str(user_id),
                    "phase": current_phase,
                    "new_phase": new_phase,
                },
            )

            total_choices = UserChoiceService._count_user_choices(db, user_id)

            # Calculate statistics
            actions = [choice.action for choice in created_choices]
            likes = sum(1 for a in actions if a == ChoiceType.LIKE)
            passes = sum(1 for a in actions if a == ChoiceType.PASS)
            prefers = sum(1 for a in actions if a == ChoiceType.PREFER)

            return {
                "success": True,
                "choices_created": 20,
                "phase_completed": current_phase,
                "current_phase": new_phase if new_phase != "COMPLETED" else 3,
                "phase_progress": f"{new_position - 1 if new_phase != 'COMPLETED' else 20}/20",
                "total_choices": total_choices,
                "all_completed": new_phase == "COMPLETED",
                "statistics": {
                    "likes": likes,
                    "passes": passes,
                    "prefers": prefers,
                }
            }

        except AppException:
            db.rollback()
            raise

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating batch choices: {e}", exc_info=True)
            raise

    @staticmethod
    def get_user_progress(db: Session, user_id: UUID) -> dict:
        """
        Get user's current progress across all phases

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Dictionary with progress information
        """
        try:
            # Validate user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise AppException(
                    error_code="error.user.not-found",
                    message="User not found",
                    status_code=404,
                )

            # Count choices per phase
            phase_counts = {}
            for phase in [1, 2, 3]:
                count = (
                    db.query(UserChoice)
                    .filter(UserChoice.user_id == user_id, UserChoice.phase == phase)
                    .count()
                )
                phase_counts[phase] = count

            total_choices = sum(phase_counts.values())

            # Determine current phase and position
            current_phase, position = UserChoiceService._get_current_phase_and_position(
                db, user_id
            )

            # Calculate completion status
            phase_1_completed = phase_counts[1] >= 20
            phase_2_completed = phase_counts[2] >= 20
            phase_3_completed = phase_counts[3] >= 20
            all_completed = total_choices >= 60

            # Phase progress string
            if current_phase == "COMPLETED":
                phase_progress = "20/20"
            else:
                current_phase_count = phase_counts.get(current_phase, 0)
                phase_progress = f"{current_phase_count}/20"

            return {
                "user_id": str(user_id),
                "current_phase": current_phase if not all_completed else 3,
                "phase_progress": phase_progress,
                "total_choices": total_choices,
                "phase_1_completed": phase_1_completed,
                "phase_1_count": phase_counts[1],
                "phase_2_completed": phase_2_completed,
                "phase_2_count": phase_counts[2],
                "phase_3_completed": phase_3_completed,
                "phase_3_count": phase_counts[3],
                "all_completed": all_completed,
            }

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error getting user progress: {e}", exc_info=True)
            raise

    @staticmethod
    def _get_current_phase_and_position(db: Session, user_id: UUID) -> Tuple[int | str, int]:
        """
        Calculate current phase and position for user

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Tuple of (phase, position)
            phase can be 1, 2, 3, or "COMPLETED"
            position is 1-20
        """
        total_choices = UserChoiceService._count_user_choices(db, user_id)

        if total_choices < 20:
            return 1, total_choices + 1
        elif total_choices < 40:
            return 2, total_choices - 19
        elif total_choices < 60:
            return 3, total_choices - 39
        else:
            return "COMPLETED", 60

    @staticmethod
    def _count_user_choices(db: Session, user_id: UUID) -> int:
        """Count total choices for a user"""
        return db.query(UserChoice).filter(UserChoice.user_id == user_id).count()

    @staticmethod
    def get_user_choices(
        db: Session, user_id: UUID, phase: Optional[int] = None
    ) -> dict:
        """
        Get user's choices with optional phase filter

        Args:
            db: Database session
            user_id: User UUID
            phase: Optional phase filter (1, 2, 3)

        Returns:
            Dictionary with choices list and statistics
        """
        try:
            # Validate user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise AppException(
                    error_code="error.user.not-found",
                    message="User not found",
                    status_code=404,
                )

            # Query choices
            query = db.query(UserChoice).filter(UserChoice.user_id == user_id)

            if phase:
                if phase not in [1, 2, 3]:
                    raise AppException(
                        error_code="error.validation.invalid-input",
                        message="Phase must be 1, 2, or 3",
                        status_code=400,
                    )
                query = query.filter(UserChoice.phase == phase)

            choices = query.order_by(UserChoice.created_at).all()

            # Calculate statistics
            likes = sum(1 for c in choices if c.action == ChoiceType.LIKE)
            passes = sum(1 for c in choices if c.action == ChoiceType.PASS)
            prefers = sum(1 for c in choices if c.action == ChoiceType.PREFER)

            return {
                "total": len(choices),
                "phase_filter": phase,
                "choices": [
                    {
                        "id": str(choice.id),
                        "pool_image": {
                            "id": str(choice.pool_image_id),
                            "image_url": choice.pool_image.image_URL,
                            "person_code": choice.pool_image.person_code,
                        },
                        "action": choice.action.value,
                        "phase": choice.phase,
                        "position": choice.position_in_phase,
                        "response_time_ms": choice.response_time_ms,
                        "created_at": choice.created_at.isoformat() if choice.created_at else None,
                    }
                    for choice in choices
                ],
                "statistics": {
                    "likes": likes,
                    "passes": passes,
                    "prefers": prefers,
                },
            }

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error getting user choices: {e}", exc_info=True)
            raise
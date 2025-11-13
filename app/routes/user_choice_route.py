import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exception import AppException
from app.models.user import User
from app.schemas.user_choice import (
    ChoiceSubmitRequest,
    ChoiceSubmitResponse,
    UserProgressResponse,
    UserChoicesListResponse,
)
from app.services.user_choice_service import UserChoiceService

logger = logging.getLogger(__name__)

choice_router = APIRouter(prefix="/choices", tags=["choices"])


def get_current_user(
    authorization: str = Header(...), db: Session = Depends(get_db)
) -> User:
    """
    Get current user from session token

    Args:
        authorization: Bearer token from header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token invalid or user not found
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    session_token = authorization.replace("Bearer ", "")

    user = db.query(User).filter(User.session_token == session_token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        )

    return user


@choice_router.post(
    "",
    response_model=ChoiceSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a choice for a pool image",
)
def submit_choice(
    request: ChoiceSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit a choice (LIKE/PASS/PREFER) for a pool image

    - **pool_image_id**: UUID of the pool image
    - **action**: One of LIKE, PASS, or PREFER
    - **response_time_ms**: Optional response time in milliseconds

    The system will:
    1. Validate the choice
    2. Record it in the database
    3. Update pool image statistics
    4. Return current progress
    """
    try:
        result = UserChoiceService.create_choice(
            db=db,
            user_id=current_user.id,
            pool_image_id=request.pool_image_id,
            action=request.action,
            response_time_ms=request.response_time_ms,
        )

        return ChoiceSubmitResponse(
            choice_id=result["choice_id"],
            current_phase=result["current_phase"],
            phase_progress=result["phase_progress"],
            total_choices=result["total_choices"],
            all_completed=result["all_completed"],
        )

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error("Error submitting choice", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit choice: {str(e)}",
        )


@choice_router.get(
    "/progress",
    response_model=UserProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's current progress",
)
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get user's progress across all phases

    Returns:
    - Current phase (1, 2, or 3)
    - Progress in current phase (e.g., "15/20")
    - Total choices made
    - Completion status for each phase
    """
    try:
        progress = UserChoiceService.get_user_progress(db=db, user_id=current_user.id)

        return UserProgressResponse(**progress)

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error("Error getting progress", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get progress: {str(e)}",
        )


@choice_router.get(
    "/me",
    response_model=UserChoicesListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's choices",
)
def get_my_choices(
    phase: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get user's choices with optional phase filter

    Query Parameters:
    - **phase**: Optional filter by phase (1, 2, or 3)

    Returns list of choices with:
    - Choice details
    - Pool image information
    - Action taken
    - Statistics (likes, passes, prefers)
    """
    try:
        result = UserChoiceService.get_user_choices(
            db=db, user_id=current_user.id, phase=phase
        )

        return UserChoicesListResponse(**result)

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error("Error getting user choices", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get choices: {str(e)}",
        )
        
        

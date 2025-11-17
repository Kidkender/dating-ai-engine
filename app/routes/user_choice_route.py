import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..constants.error_constant import ERROR_CHOICE_FETCH_FAILED, ERROR_CHOICE_PROGRESS_FETCH_FAILED, ERROR_CHOICE_SUBMIT_FAILED

from ..core.auth_dependency import AuthResult, get_current_user
from app.core.database import get_db
from app.core.exception import AppException
from app.schemas.user_choice import (
    BatchChoiceSubmitRequest,
    BatchChoiceSubmitResponse,
    ChoiceSubmitRequest,
    ChoiceSubmitResponse,
    UserProgressResponse,
    UserChoicesListResponse,
)
from app.services.user_choice_service import UserChoiceService

logger = logging.getLogger(__name__)

choice_router = APIRouter(prefix="/choices", tags=["choices"])


@choice_router.post(
    "",
    response_model=ChoiceSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a choice for a pool image",
)
def submit_choice(
    request: ChoiceSubmitRequest,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_user),
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
            user_id=auth.user.id,
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
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ERROR_CHOICE_SUBMIT_FAILED
        )


@choice_router.post(
    "/batch",
    response_model=BatchChoiceSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit exactly 20 choices for a phase (REQUIRED)",
)
def submit_batch_choices(
    request: BatchChoiceSubmitRequest,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_user),
):
    """
    Submit exactly 20 choices (LIKE/PASS/PREFER) for a phase

    **STRICT REQUIREMENTS:**
    - Must submit exactly 20 choices
    - All choices must be for images eligible for current phase
    - Cannot vote for same image twice
    - Cannot vote for images already voted in previous phases
    - If any validation fails, entire batch is rejected

    **AUTO-REDO PHASE:**
    - If user has incomplete choices in current phase (< 20), they will be deleted
    - User must redo the entire phase with 20 new choices

    **Request body example:**
    ```json
    {
        "choices": [
            {
                "pool_image_id": "uuid-1",
                "action": "LIKE",
                "response_time_ms": 1500
            },
            {
                "pool_image_id": "uuid-2",
                "action": "PASS",
                "response_time_ms": 800
            },
            ... (exactly 20 items total)
        ]
    }
    ```

    **Response:**
    - Success: Phase completed, returns statistics
    - Failure: Entire batch rejected with detailed error

    **Phase progression:**
    - Phase 1 (0-19 choices): Random diverse selection
    - Phase 2 (20-39 choices): Based on Phase 1 preferences
    - Phase 3 (40-59 choices): Based on Phase 1 + 2 preferences
    - Completed (60+ choices): All phases done
    """
    try:
        # Convert choices to dict format
        choices_data = [
            {
                "pool_image_id": choice.pool_image_id,
                "action": choice.action,
                "response_time_ms": choice.response_time_ms,
            }
            for choice in request.choices
        ]

        result = UserChoiceService.create_batch_choices(
            db=db,
            user_id=auth.user.id,
            choices_data=choices_data,
        )

        likes = result["statistics"]["likes"]
        passes = result["statistics"]["passes"]
        prefers = result["statistics"]["prefers"]

        message = f"Phase {result['phase_completed']} completed successfully! "
        message += f"Stats: {likes} likes, {passes} passes, {prefers} prefers"

        if result["all_completed"]:
            message += " | All phases completed! 🎉"

        return BatchChoiceSubmitResponse(
            message=message,
            success=result["success"],
            choices_created=result["choices_created"],
            phase_completed=result["phase_completed"],
            current_phase=result["current_phase"],
            phase_progress=result["phase_progress"],
            total_choices=result["total_choices"],
            all_completed=result["all_completed"],
            statistics=result["statistics"],
        )

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error("Error submitting batch choices", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ERROR_CHOICE_SUBMIT_FAILED
        )

@choice_router.get(
    "/progress",
    response_model=UserProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's current progress",
)
def get_progress(
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_user),
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
        progress = UserChoiceService.get_user_progress(db=db, user_id=auth.user.id)

        return UserProgressResponse(**progress)

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error("Error getting progress", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ERROR_CHOICE_PROGRESS_FETCH_FAILED
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
    auth: AuthResult = Depends(get_current_user),
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
            db=db, user_id=auth.user.id, phase=phase
        )

        return UserChoicesListResponse(**result)

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error("Error getting user choices", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ERROR_CHOICE_FETCH_FAILED 
        )
        
     

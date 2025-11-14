import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.auth_dependency import AuthResult, get_current_user
from app.core.database import get_db
from app.core.exception import AppException
from app.models.user import User
from app.schemas.recommendation import (
    PreferenceProfileResponse,
    GenerateRecommendationsResponse,
)
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)

recommendation_router = APIRouter(prefix="/recommendations", tags=["recommendations"])



@recommendation_router.get(
    "/profile",
    response_model=PreferenceProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user's preference profile",
)
def get_preference_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get user's preference profile built from all 3 phases

    **Requirements:**
    - User must have completed all 3 phases (60 choices)
    - User status must be COMPLETED

    **Returns:**
    - Preference vector statistics
    - Choice breakdown by phase
    - Preference strength score
    """
    try:
        profile = RecommendationService.build_user_preference_profile(
            db=db, user_id=current_user.id
        )

        return PreferenceProfileResponse(**profile)

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error("Error getting preference profile", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get preference profile: {str(e)}",
        )


@recommendation_router.post(
    "/generate",
    response_model=GenerateRecommendationsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate personalized recommendations",
)
def generate_recommendations(
    # request: GenerateRecommendationsRequest,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_user),
):
    """
    Generate personalized user recommendations based on preference profile

    **How it works:**
    1. Builds user's preference vector from all 3 phases
    2. Weights Phase 3 choices highest (most refined preferences)
    3. Calculates similarity with all other active users
    4. Returns top matches ranked by similarity score

    **Parameters:**
    - **limit**: Max recommendations to generate (1-100, default 50)
    - **min_similarity**: Minimum similarity threshold (0-1, default 0.5)

    **Requirements:**
    - User must have completed all 3 phases

    **Returns:**
    - Total recommendations generated
    - Saved count
    - Top similarity score
    - Preference profile details
    """
    try:
        # Generate recommendations
        recommendations = RecommendationService.generate_recommendations(
            db=db,
            user_id=auth.user.id,
            # limit=request.limit,
            # min_similarity=request.min_similarity,
            limit=10,
            min_similarity=0.5
        )

        if not recommendations:
            return GenerateRecommendationsResponse(
                message="No recommendations found matching criteria",
                total_generated=0,
                saved_count=0,
                top_similarity_score=0.0,
                preference_profile=RecommendationService.build_user_preference_profile(
                    db, auth.user.id
                ),
            )

        # Save to database
        saved = RecommendationService.save_recommendations(
            db=db,
            user_id=auth.user.id,
            recommendations=recommendations,
        )

        # Get profile
        profile = RecommendationService.build_user_preference_profile(
            db, auth.user.id
        )

        top_score = recommendations[0][1] if recommendations else 0.0

        return GenerateRecommendationsResponse(
            message=f"Successfully generated {len(recommendations)} recommendations",
            total_generated=len(recommendations),
            saved_count=len(saved),
            top_similarity_score=top_score,
            preference_profile=profile,
        )

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error("Error generating recommendations", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}",
        )


@recommendation_router.get(
    "/me",
    # response_model=Any,
    status_code=status.HTTP_200_OK,
    summary="Get my saved recommendations",
)
async def get_my_recommendations(
    limit: int = 20,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_user),
):
    """
    Get saved recommendations for current user

    **Parameters:**
    - **limit**: Number of recommendations to return (default 20)

    **Returns:**
    - List of recommended users
    - Ranked by similarity score
    - Includes user info and primary image
    """
    try:

        recommendations = await RecommendationService.get_user_recommendations(
            db=db,
            user_id=auth.user.id,
            token=auth.token,
            limit=limit,
        )
        return recommendations

        # if not recommendations:
        #     return RecommendationsResponse(
        #         message="No recommendations found. Generate recommendations first.",
        #         total_recommendations=0,
        #         recommendations=[],
        #     )

        # return RecommendationsResponse(
        #     message=f"Found {len(recommendations)} recommendations",
        #     total_recommendations=len(recommendations),
        #     recommendations=recommendations,
        # )

    except Exception as e:
        logger.error("Error getting recommendations", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}",
        )
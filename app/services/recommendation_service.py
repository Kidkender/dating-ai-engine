
import logging
from typing import List, Tuple
from uuid import UUID
import numpy as np
from sqlalchemy.orm import Session

from app.models.user import User, UserStatus
from app.models.user_choice import UserChoice, ChoiceType
from app.models.user_image import UserImage
from app.models.recommendation import Recommendation
from app.core.exception import AppException
from app.core.config import settings
from app.utils.http_client import http_client
logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for building user preferences and generating recommendations"""

    def __init__(self, db: Session):
        self.db = db

    def build_user_preference_profile(self, user_id: UUID) -> dict:
        """
        Build user's preference profile from all 3 phases

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Dictionary with preference profile data
        """
        try:
            # Validate user completed all phases
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise AppException(
                    error_code="error.user.not-found",
                    message="User not found",
                    status_code=404,
                )

            if user.status != UserStatus.COMPLETED:
                raise AppException(
                    error_code="error.user.not-completed",
                    message="User has not completed all phases",
                    status_code=400,
                )

            # Get all choices
            all_choices = (
                self.db.query(UserChoice)
                .filter(UserChoice.user_id == user_id)
                .all()
            )

            if len(all_choices) < 60:
                raise AppException(
                    error_code="error.user.incomplete-choices",
                    message=f"User has only {len(all_choices)} choices, need 60",
                    status_code=400,
                )

            # Separate by phase and action
            phase_1_likes = [
                c for c in all_choices
                if c.phase == 1 and c.action in [ChoiceType.LIKE, ChoiceType.PREFER]
            ]
            phase_2_likes = [
                c for c in all_choices
                if c.phase == 2 and c.action in [ChoiceType.LIKE, ChoiceType.PREFER]
            ]
            phase_3_likes = [
                c for c in all_choices
                if c.phase == 3 and c.action in [ChoiceType.LIKE, ChoiceType.PREFER]
            ]

            # Extract embeddings with weights
            # Phase 3 = highest weight (most refined preferences)
            # Phase 2 = medium weight
            # Phase 1 = lowest weight (initial exploration)
            weighted_embeddings = []

            for choice in phase_1_likes:
                if (choice.pool_image and choice.pool_image.face_embedding is not None and len(choice.pool_image.face_embedding)):
                    
                    embedding = np.array(choice.pool_image.face_embedding)
                    weight = 2.0 if choice.action == ChoiceType.PREFER else 1.0
                    weighted_embeddings.append((embedding, weight))

            for choice in phase_2_likes:
                if (choice.pool_image and choice.pool_image.face_embedding is not None and len(choice.pool_image.face_embedding)):
                    embedding = np.array(choice.pool_image.face_embedding)
                    weight = 3.0 if choice.action == ChoiceType.PREFER else 2.0
                    weighted_embeddings.append((embedding, weight))

            for choice in phase_3_likes:
                if (choice.pool_image and choice.pool_image.face_embedding is not None and len(choice.pool_image.face_embedding)):
                    embedding = np.array(choice.pool_image.face_embedding)
                    weight = 5.0 if choice.action == ChoiceType.PREFER else 3.0
                    weighted_embeddings.append((embedding, weight))

            if not weighted_embeddings:
                raise AppException(
                    error_code="error.preference.no-likes",
                    message="User has no LIKE/PREFER choices",
                    status_code=400,
                )

            # Calculate weighted average preference vector
            embeddings = np.array([e for e, w in weighted_embeddings])
            weights = np.array([w for e, w in weighted_embeddings])
            
            preference_vector = np.average(embeddings, axis=0, weights=weights)
            
            # Normalize
            preference_vector = preference_vector / (np.linalg.norm(preference_vector) + 1e-8)

            # Calculate statistics
            total_likes = len(phase_1_likes) + len(phase_2_likes) + len(phase_3_likes)
            total_passes = sum(1 for c in all_choices if c.action == ChoiceType.PASS)
            total_prefers = sum(1 for c in all_choices if c.action == ChoiceType.PREFER)

            profile = {
                "user_id": str(user_id),
                "preference_vector": preference_vector.tolist(),
                "vector_dimension": len(preference_vector),
                "total_choices": len(all_choices),
                "total_likes": total_likes,
                "total_passes": total_passes,
                "total_prefers": total_prefers,
                "phase_1_likes": len(phase_1_likes),
                "phase_2_likes": len(phase_2_likes),
                "phase_3_likes": len(phase_3_likes),
                "preference_strength": float(np.mean(weights)),
            }

            logger.info(
                f"Built preference profile for user {user_id}",
                extra={
                    "user_id": str(user_id),
                    "total_likes": total_likes,
                    "preference_strength": profile["preference_strength"],
                },
            )

            return profile

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error building preference profile: {e}", exc_info=True)
            raise

    def generate_recommendations(
        self,
        user_id: UUID,
        limit: int = 50,
        min_similarity: float = 0.5
    ) -> List[Tuple[User, float]]:
        """
        Generate personalized recommendations for user

        Args:
            db: Database session
            user_id: User UUID
            limit: Maximum number of recommendations
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of (User, similarity_score) tuples, sorted by score DESC
        """
        try:
            profile = self.build_user_preference_profile(user_id)
            preference_vector = np.array(profile["preference_vector"])

            # Get current user's gender to filter opposite/compatible gender
            current_user = self.db.query(User).filter(User.id == user_id).first()
            if not current_user:
                raise AppException(
                    error_code="error.user.not-found",
                    message="User not found",
                    status_code=404,
                )

            # Get all other ACTIVE users with images
            candidate_users = (
                self.db.query(User)
                .filter(
                    User.id != user_id,
                    # User.status == UserStatus.ACTIVE,
                )
                .all()
            )

            if not candidate_users:
                logger.warning(f"No candidate users found for {user_id}")
                return []

            recommendations = []

            for candidate in candidate_users:
                primary_image = (
                    self.db.query(UserImage)
                    .filter(
                        UserImage.user_id == candidate.id,
                        UserImage.is_primary == True,
                    )
                    .first()
                )
                
                if not primary_image:
                    continue

                if primary_image.face_embedding is None:
                    continue

                if len(primary_image.face_embedding) == 0:
                    continue

           

                candidate_vector = np.array(primary_image.face_embedding)
                candidate_vector = candidate_vector / (np.linalg.norm(candidate_vector) + 1e-8)
                
                similarity = float(np.dot(preference_vector, candidate_vector))
                if similarity >= min_similarity:
                    recommendations.append((candidate, similarity))

            recommendations.sort(key=lambda x: x[1], reverse=True)

            # Limit results
            recommendations = recommendations[:limit]

            logger.info(
                f"Generated {len(recommendations)} recommendations for user {user_id}",
                extra={
                    "user_id": str(user_id),
                    "total_candidates": len(candidate_users),
                    "recommendations": len(recommendations),
                    "top_similarity": recommendations[0][1] if recommendations else 0,
                },
            )

            return recommendations

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}", exc_info=True)
            raise

    def save_recommendations(
        self,
        user_id: UUID,
        recommendations: List[Tuple[User, float]]
    ) -> List[Recommendation]:
        """
        Save recommendations to database

        Args:
            db: Database session
            user_id: User UUID
            recommendations: List of (User, similarity_score) tuples

        Returns:
            List of created Recommendation objects
        """
        try:
            self.db.query(Recommendation).filter(
                Recommendation.user_id == user_id
            ).delete()

            saved_recommendations = []

            for rank, (candidate, similarity) in enumerate(recommendations, 1):
                recommendation = Recommendation(
                    user_id=user_id,
                    recommended_user_id=candidate.id,
                    similarity_score=similarity,
                    rank=rank,
                )

                self.db.add(recommendation)
                saved_recommendations.append(recommendation)

            self.db.commit()

            logger.info(
                f"Saved {len(saved_recommendations)} recommendations for user {user_id}",
                extra={"user_id": str(user_id), "count": len(saved_recommendations)},
            )

            return saved_recommendations

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving recommendations: {e}", exc_info=True)
            raise

    async def get_user_recommendations(
        self,
        user_id: UUID,
        token: str,
        limit: int = 20
    ) -> List[dict]:
        """
        Get saved recommendations for user

        Args:
            db: Database session
            user_id: User UUID
            limit: Maximum number to return

        Returns:
            List of recommendation dictionaries
        """
        try:
            recommendations = (
                self.db.query(Recommendation)
                .filter(Recommendation.user_id == user_id)
                .order_by(Recommendation.rank)
                .limit(limit)
                .all()
            )

            recommend_external_id = []
            for rec in recommendations:
                external_id = rec.recommended_user.external_user_id
                if external_id:  
                    recommend_external_id.append(external_id)
                
            recommend_external_id_str =[str(uid) for uid in recommend_external_id]
            
            body= {
                "userIds": recommend_external_id_str
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = await http_client.post(
                f"{settings.DATING_APP_BASE_URL}/api/dating/profiles",
                headers=headers,
                json=body
            )
            


            return response.json()

        except Exception as e:
            logger.error(f"Error getting recommendations: {e}", exc_info=True)
            raise
        
    def remove_all_recommendation(self, user_id: UUID):
        recommendation = self.db.query(Recommendation).filter(Recommendation.user_id == user_id).all()
        if len(recommendation) ==0 :
            logger.info(f"Not found recommendation for user {user_id}")

        self.db.query(Recommendation).filter(Recommendation.user_id == user_id).delete()
        self.db.flush()
        logger.info(f"[DONE] Reset all recommendation for user {user_id}")
    
        
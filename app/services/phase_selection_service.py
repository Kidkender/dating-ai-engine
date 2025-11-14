import logging
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
import random
import numpy as np
from ..core.exception import AppException

from ..models.pool_image import PoolImage
from ..models.user_choice import ChoiceType, UserChoice
logger = logging.getLogger(__name__)

class PhaseSelectionService:
    """Service for intelligent phase-based image selection"""
    
    @staticmethod
    def get_images_for_user(
        db: Session,
        user_id: UUID,
        phase: int,
        limit: int = 20
    ) -> List[PoolImage]:
        
        if phase not in [1,2,3]:
          raise AppException(
              error_code="error.validation.invalid-phase",
              message="Phase must be 1, 2 or 3"
          )
        
        if phase == 1:
            return PhaseSelectionService._select_phase_1_images(db, user_id, limit)
        elif phase == 2:
            return PhaseSelectionService._select_phase_2_images(db, user_id, limit)
        else:
            return PhaseSelectionService._select_phase_3_images(db, user_id, limit)
        
    @staticmethod
    def _select_phase_1_images(
            db: Session,
            user_id: UUID,
            limit: int
            ) -> List[PoolImage]:
        logger.info("Selecting Phase 1 images for user {user_id}")

        voted_image_ids = (
                db.query(UserChoice.pool_image_id)
                .filter(UserChoice.user_id == user_id).all()
                )
        voted_ids = [img_id[0] for img_id in voted_image_ids]

        query = db.query(PoolImage).filter(
                PoolImage.is_active == True,
                PoolImage.phase_eligibility.any(1)
                )

        if voted_ids:
            query = query.filter(~PoolImage.id.in_(voted_ids))

        available_images = query.all()

        if len(available_images) < limit:
            logger.warning(
                f"Only {len(available_images)} images available for phase 1, requested {limit}"
            ) 
            return available_images

        selected_images = random.sample(available_images, limit)
        logger.info(f"Selected {len(selected_images)} images for phase 1")
        return selected_images

    @staticmethod
    def _select_phase_2_images(
            db: Session,
            user_id: UUID,
            limit: int
            ) -> List[PoolImage]:
        # phase_1_preferences = (db.query(UserChoice.user_id == user_id, UserChoice.phase == 1, UserChoice.action.in_([ChoiceType.LIKE, ChoiceType.PREFER]))).all()
        phase_1_preferences = (
            db.query(UserChoice)
            .filter(
                UserChoice.user_id == user_id,
                UserChoice.phase == 1,
                UserChoice.action.in_([ChoiceType.LIKE, ChoiceType.PREFER])
            )
            .all()
        )

        if not phase_1_preferences:
            logger.warning(f"User {user_id} has no Phase 1 preferrences, using random selection")
            return PhaseSelectionService._select_random_phase_images(db, user_id, 2, limit)

        preferred_embeddings = []
        for choice in phase_1_preferences:
            if (
                choice.pool_image is not None
                and choice.pool_image.face_embedding is not None
                and len(choice.pool_image.face_embedding) > 0
            ):
                embedding = np.array(choice.pool_image.face_embedding)
                preferred_embeddings.append(embedding)


        if not preferred_embeddings:
            logger.warning(f"No valid embeddings found, using random selection")

            return PhaseSelectionService._select_random_phase_images(db, user_id, 2, limit)

        preference_vector = np.mean(preferred_embeddings, axis=0)

        voted_image_ids = (
                db.query(UserChoice.pool_image_id).filter(UserChoice.user_id == user_id).all()
                )
        voted_ids = [img_id[0]  for img_id in voted_image_ids]

        query = db.query(PoolImage).filter(
                PoolImage.is_active == True,
                PoolImage.phase_eligibility.any(2)
                )

        if voted_ids: 
            query = query.filter(~PoolImage.id.in_(voted_ids))

        available_images = query.all()

        if not available_images:
            logger.warning(f"No available Phase 2 images")
            return []   
        
        similarities = []
        for image in available_images:
            if image.face_embedding is not None and len(image.face_embedding) > 0:
                image_embedding = np.array(image.face_embedding)
                similarity = PhaseSelectionService._cosine_similarity(
                    preference_vector, image_embedding
                )
                similarities.append((image, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)


        selected_images = [img for img, score in similarities[:limit]]

        logger.info(f"Selected {len(selected_images)} images for Phase 2 based on {len(phase_1_preferences)} preferrences")

        return selected_images

    @staticmethod
    def _select_phase_3_images(
            db: Session,
            user_id: UUID,
            limit: int
            ) -> List[PoolImage]:
            
        phase_1_preferrences = (db.query(UserChoice)
                                .filter(UserChoice.user_id == user_id,
                                UserChoice.phase == 1,
                                UserChoice.action.in_([ChoiceType.LIKE, ChoiceType.PREFER
                            ])).all())
        phase_2_preferrences = (db.query(UserChoice)
                                .filter(UserChoice.user_id == user_id,
                                UserChoice.phase == 2,
                                UserChoice.action.in_([ChoiceType.LIKE, ChoiceType.PREFER
                            ])).all())
        all_preferences  = phase_2_preferrences + phase_1_preferrences
        
        if not all_preferences :
            logger.warning(f"User {user_id} has no preferrences, using random selection")
            return PhaseSelectionService._select_random_phase_images(db, user_id, 3, limti)
        
        preferred_embeddings = []
        for choice in all_preferences:
            # if choice.pool_image and choice.pool_image.face_embedding:
            if choice.pool_image is not None and len(choice.pool_image.face_embedding) > 0:
                embedding = np.array(choice.pool_image.face_embedding)

                weight = 1.0 if choice.phase == 2 else 0.5
                preferred_embeddings.append(embedding * weight)

        if not preferred_embeddings:
            logger.warning(f"No valid embedding found, using random selection")
            return PhaseSelectionService._select_random_phase_images(db, user_id, 3, limit)

        preferred_vector = np.mean(preferred_embeddings, axis=0)

        voted_image_ids = (
                db.query(UserChoice.pool_image_id).filter(
                    UserChoice.user_id == user_id
                    ).all())

        voted_ids = [img_id[0] for img_id in voted_image_ids]

        query = db.query(PoolImage).filter(
            PoolImage.is_active == True
            ,PoolImage.phase_eligibility.any(3)
            )

        if voted_ids: 
            query = query.filter(~PoolImage.id.in_(voted_ids))

        available_images = query.all()

        if not available_images:
            logger.warning(f"No available Phase 3 images")
            return []

        similarities= []
        
        for image in available_images:
            if image.face_embedding is not None:
                image_embedding = np.array(image.face_embedding)
                similarity = PhaseSelectionService._cosine_similarity(
                    preferred_vector, image_embedding
                )
                similarities.append((image, similarity))
                
        similarities.sort(key= lambda x: x[1], reverse=True)
        
        selected_images = [img for img, score in similarities[:limit]]
        
        logger.info(f"Selected {len(selected_images)} images for Phase 3 based on {len(all_preferences)} preferences")
        return selected_images
    
    @staticmethod
    def _select_random_phase_images(
        db: Session,
        user_id: UUID,
        phase: int, 
        limit: int
    ) -> List[PoolImage]:
        
        voted_image_ids = (
            db.query(UserChoice.pool_image_id).filter(UserChoice.user_id == user_id).all()
            
        )
        
        voted_ids = [img_id[0] for img_id in voted_image_ids]
        
        query = db.query(PoolImage).filter(
            PoolImage.is_active == True,
            PoolImage.phase_eligibility.any_(phase)
            
        )
        
        if voted_ids:
            query = query.filter(~PoolImage.id.in_(voted_ids))
        
        available_images = query.all()
        
        if len(available_images) <= limit:
            return available_images
        
        return random.sample(available_images, limit)
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (-1 to 1, higher is more similar)
        """   
        vec1_norm = vec1 /(np.linalg.norm(vec1) + 1e-8)
        vec2_norm = vec2 /(np.linalg.norm(vec2) + 1e-8)
        
        similarity = np.dot(vec1_norm, vec2_norm)
        
        return float(similarity)
    
        
                



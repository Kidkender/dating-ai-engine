from typing import Optional
from pydantic import BaseModel, Field


class PreferenceProfileResponse(BaseModel):
    """User preference profile response"""
    
    user_id: str
    vector_dimension: int
    total_choices: int
    total_likes: int
    total_passes: int
    total_prefers: int
    phase_1_likes: int
    phase_2_likes: int
    phase_3_likes: int
    preference_strength: float
    message: str = "Preference profile built successfully"


class RecommendedUser(BaseModel):
    """Single recommended user"""
    
    rank: int
    user_id: str
    name: Optional[str]
    similarity_score: float
    image_url: Optional[str]
    created_at: Optional[str]


class RecommendationsResponse(BaseModel):
    """List of recommendations response"""
    
    message: str
    total_recommendations: int
    recommendations: list[RecommendedUser]


class GenerateRecommendationsRequest(BaseModel):
    """Request to generate recommendations"""
    
    limit: int = Field(50, ge=1, le=100, description="Max recommendations to generate")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold")


class GenerateRecommendationsResponse(BaseModel):
    """Response after generating recommendations"""
    
    message: str
    total_generated: int
    saved_count: int
    top_similarity_score: float
    preference_profile: PreferenceProfileResponse
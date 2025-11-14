import logging

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from ..services.auth_service import AuthService

from ..models.user import User
from .database import get_db


logger = logging.getLogger(__name__)

class AuthResult:
    def __init__(self, user: User, token: str):
        self.user = user
        self.token = token

async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
)-> AuthResult: 
    """
    Validate access token and return current user

    Args:
        authorization: Bearer token from Authorization header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token invalid or user not found
    """
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
        
    access_token = authorization.replace("Bearer ", "").strip()
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is required",
        )
    
    is_valid, user_id,email, error_message = await AuthService.validate_token(access_token)
    
    
    if not is_valid:
        logger.warning(
            f"Token validation failed: {error_message}",
            extra={"error": error_message}
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {error_message}"
        )
        
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    try: 
        user = AuthService.get_or_create_user(db=db, user_id=user_id, email=email)
        return AuthResult(user, access_token)

    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to authenticate user: {str(e)}",
        )
    
async def get_current_user_optional(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> AuthResult | None:
    """
    Optional authentication - returns user if valid token, None otherwise

    Args:
        authorization: Optional Bearer token
        db: Database session

    Returns:
        User object or None
    """
    if not authorization:
        return None

    try:
        return await get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None
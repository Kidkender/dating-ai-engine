import logging

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from ..constants.error_constant import ERROR_AUTH_AUTHENTICATION_FAILED, ERROR_AUTH_INVALID_OR_EXPIRED_TOKEN, ERROR_AUTH_USER_ID_NOT_FOUND

from .exception import AppException

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

    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
        
    access_token = authorization.replace("Bearer ", "").strip()
    print(f"access token: {access_token}")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is required",
    
        )
    
    auth_service = AuthService(db)

    is_valid, user_id,email, error_message, data = await auth_service.validate_token( access_token)
    
    print("user id:", user_id)
    if not is_valid:
        logger.warning(
            f"Token validation failed: {error_message}",
            extra={"error": error_message}
        )
        
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            # detail=f"Invalid or expired token: {error_message}"
            error_code=ERROR_AUTH_INVALID_OR_EXPIRED_TOKEN
        )
        
    if not user_id:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ERROR_AUTH_USER_ID_NOT_FOUND
        )
    
    try: 
        user = await auth_service.get_or_create_user( user_id=user_id, email=email, data=data)
        return AuthResult(user, access_token)

    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        raise AppException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ERROR_AUTH_AUTHENTICATION_FAILED
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
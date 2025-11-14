import logging
from typing import Optional, Tuple
import httpx
from sqlalchemy.orm import Session

from app.utils.http_client import http_client

from ..core.exception import AppException

from ..models.user import User, UserStatus

from app.core.config import settings


logger = logging.getLogger(__name__)
class AuthService: 
    
    @staticmethod
    async def validate_token(access_token:  str) -> Tuple[bool, Optional[str],Optional[str], Optional[str]]:
        """
        Validate access token with main backend's healthCheck endpoint

        Args:
            access_token: Access token from Authorization header

        Returns:
            Tuple of (is_valid, user_id, error_message)
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = await http_client.get(
                f"{settings.DATING_APP_BASE_URL}/api/users/getCurrentUser",
                headers = headers
            )
            
            if response.status_code != 200:
                logger.warning(
                    f"Token validation failed with status {response.status_code}",
                    extra={"status_code": response.status_code}
                )
                return False, None, None, f"Invalid token: HTTP {response.status_code}"

            data = response.json()
            user_id = data.get("data", {}).get("id")
            email = data.get("data", {}).get("userEmail")
            
            
            if not user_id:
                logger.error(
                    "Invalid response format from getCurrentUser",
                    extra={"response": data}
                )
                return False, None, None, 'Invalid response format'

            logger.info(
                f"Token validated successfully for user {user_id}",
                extra={"user_id": user_id},
            )

            return True, user_id, email, None
         
        except httpx.TimeoutException:
            logger.error("Token validation timeout")
            return False, None, None,"Token validation timeout"

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token validation: {e}", exc_info=True)
            return False, None, None, f"HTTP error: {str(e)}"

        except Exception as e:
            logger.error(f"Error validating token: {e}", exc_info=True)
            return False, None, None,f"Validation error: {str(e)}"
        
    @staticmethod
    def get_or_create_user(db: Session, user_id: str, email: Optional[str] = None) -> User: 
        
        
        try: 
            user = (db.query(User).filter(User.external_user_id == user_id).first())
            
            if user:
                return user

            if email:
                user = db.query(User).filter(User.email == email).first()
                
            if email:
                user = db.query(User).filter(User.email == email).first()
                
                if user:
                    user.external_user_id = user_id
                    db.commit()
                    db.refresh(user)
                    logger.info(
                        f"Linked external_user_id {user_id} to existing user",
                        extra={"user_id": str(user.id), "external_user_id": user_id}
                    )
                    return user
            
            # Create new user
            new_user = User(
                external_user_id=user_id,
                email=email or f"{user_id}@temp.com",
                session_token="",
                status=UserStatus.ONBOARDING
            )
                
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            logger.info(
                f"Created new user for external_user_id {user_id}",
                extra={"user_id": str(new_user.id), "external_user_id": user_id}
            )
                
            return new_user
            
        except Exception as e:
                db.rollback()
                logger.error(f"Error getting/creating user: {e}", exc_info=True)
                raise AppException(
                    error_code="error.user.creation-failed",
                    message=f"Failed to get/create user: {str(e)}",
                    status_code=500,
                )
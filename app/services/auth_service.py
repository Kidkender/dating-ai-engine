import logging
from typing import Optional, Tuple
import httpx
from sqlalchemy.orm import Session
from app.schemas.sync import DatingAppUser, UserInfo

from ..core.exception import AppException

from .user_sync_service import UserSyncService
from app.utils.http_client import http_client


from ..models.user import User

from app.core.config import settings


logger = logging.getLogger(__name__)
class AuthService: 
    
    def __init__(self, db: Session):
        self.db = db
    
    async def validate_token(self, access_token:  str) -> Tuple[bool, Optional[str],Optional[str], Optional[str], Optional[dict]]:
      
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = await http_client.get(
                f"{settings.DATING_APP_BASE_URL}/api/dating",
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
            
            payload = data.get("data", {})

            if not user_id:
                logger.error(
                    "Invalid response format from getCurrentUser",
                    extra={"response": payload}
                )
                return False, None, None, 'Invalid response format', None
            
            logger.info(
                f"Token validated successfully for user {user_id}",
                extra={"user_id": user_id},
            )

            return True, user_id, email, None, payload
         
        except httpx.TimeoutException:
            logger.error("Token validation timeout")
            return False, None, None,"Token validation timeout", None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token validation: {e}", exc_info=True)
            return False, None, None, f"HTTP error: {str(e)}", None
        except Exception as e:
            logger.error(f"Error validating token: {e}", exc_info=True)
            return False, None, None,f"Validation error: {str(e)}", None
        
    async def get_or_create_user(self, user_id: str, email: Optional[str] = None, data: Optional[dict] = None) -> User: 
        
        
        try: 
            user = (self.db.query(User).filter(User.external_user_id == user_id).first())
            
            if user:
                return user
            
            userName = "user_"+ user_id
            userEmail = "user_"+ user_id + "@example.com" if not email else email
            userGender = data.get("orientation")
            datingImages = data.get('datingImages')
            
            _id= data.get("id")
   
            dating_user = DatingAppUser(
                user=UserInfo(
                userName=userName,
                userEmail=userEmail,
                userGender=userGender
                ),
                datingImages=datingImages,
                id= _id,
                userId=user_id,

            )
            
            user_sync_service = UserSyncService(self.db)
            sync_result = await user_sync_service.sync_single_user(
                dating_user=dating_user,
                force_resync=False,
                min_face_confidence=0.8,
            )
            
            new_user = (self.db.query(User).filter(User.external_user_id == user_id).first())

        
            logger.info(
                f"Created new user for external_user_id {user_id}",
                extra={"user_id": str(new_user.id), "external_user_id": user_id}
            )
                
            return new_user
            
        except Exception as e:
                self.db.rollback()
                logger.error(f"Error getting/creating user: {e}", exc_info=True)
                raise AppException(
                    error_code="error.user.creation-failed",
                    message=f"Failed to get/create user: {str(e)}",
                    status_code=500,
                )
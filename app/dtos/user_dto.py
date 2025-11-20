from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from ..schemas.user import UserResponse

from ..models.user import User, UserStatus


@dataclass
class UserDTO:
    id: UUID
    email: str
    name: Optional[str]
    status: UserStatus
    external_user_id: str
    created_at: datetime
    
    @classmethod
    def from_model(cls, user: User) -> "UserDTO":
        return cls(
            id= user.id,
            email= user.email,
            name= user.name,
            status= user.status,
            external_user_id= user.external_user_id,
            created_at= user.created_at
        )
        
    def to_response(self) -> UserResponse:
        return UserResponse(
            id = self.id,
            email = self.email,
            name = self.name,
            status = self.status , 
            created_at=self.created_at
        )
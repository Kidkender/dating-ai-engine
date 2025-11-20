

from enum import Enum


class UserStatus(str, Enum):
    ONBOARDING = "ONBOARDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    
class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class ImageStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
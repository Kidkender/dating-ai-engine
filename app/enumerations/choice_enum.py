from enum import Enum

class ChoiceType(str, Enum):
    LIKE = "like"
    PASS = "pass"
    PREFER = "prefer"
from fastapi import HTTPException


class BadRequestException(HTTPException):
    def __init__(self, message: str, code: int = 400):
        super().__init__(status_code=code, detail=message)

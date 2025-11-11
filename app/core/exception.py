from typing import Any, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):

    def __init__(
        self,
        error_code: str,
        message: str | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[dict[str, Any]] = None,
    ):
        """
        Args:
            error_code: Error code constant (e.g., ERROR_USER_NOT_FOUND)
            message: Human-readable message (optional, sẽ dùng error_code nếu None)
            status_code: HTTP status code
            details: Additional context data
        """
        self.error_code = error_code
        self.details = details or {}

        display_message = message or error_code

        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code,
                "message": display_message,
                "details": self.details,
            },
        )

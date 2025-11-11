import logging
import traceback
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.core.exception import AppException

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware để handle exceptions và format response
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response

        except AppException as exc:
            # Custom app exceptions - already formatted
            logger.warning(
                f"Application error: {exc.error_code}",
                extra={
                    "error_code": exc.error_code,
                    "path": request.url.path,
                    "method": request.method,
                    "details": exc.details,
                },
            )

            # AppException extends HTTPException, FastAPI tự động handle
            # Nhưng nếu muốn custom format thì return ở đây
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,  # Already formatted in AppException
            )

        except SQLAlchemyError as exc:
            # Database errors
            logger.error(
                "Database error occurred",
                exc_info=True,
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": type(exc).__name__,
                },
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "error.database.transaction-failed",
                    "message": "Database error occurred",
                    "details": {
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                },
            )

        except Exception as exc:
            # Unexpected errors
            logger.error(
                "Unhandled exception occurred",
                exc_info=True,
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_type": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                },
            )

            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "error.internal.unexpected",
                    "message": "An unexpected error occurred",
                    "details": {
                        "error_type": type(exc).__name__,
                        # Chỉ show error message trong dev, production thì ẩn
                        # "error": str(exc),
                    },
                },
            )

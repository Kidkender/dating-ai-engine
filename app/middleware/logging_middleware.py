import time
from typing import Awaitable, Callable
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.logging_config import get_logger, request_id_var, user_id_var

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # return await super().dispatch(request, call_next)
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)

        user_id = self._extract_user_id(request)
        if user_id:
            user_id_var.set(user_id)

        start_time = time.time()

        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        try:
            response = await call_next(request)

            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            response.headers["X-request-id"] = request_id
            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Request failed",
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                },
            )
            raise

        finally:
            request_id_var.set("")
            user_id_var.set("")

    def _extract_user_id(self, request: Request) -> str | None:
        session_token = request.headers.get("Authorization")
        if session_token:
            pass

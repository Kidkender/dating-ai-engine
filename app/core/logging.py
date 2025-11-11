import logging
import sys
import json
from datetime import datetime
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""

        # Base log structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request/user context if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id

        # Add extra fields from logger.info(..., extra={...})
        if hasattr(record, "extra_fields"):
            log_data["context"] = record.extra_fields

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_data, default=str)


class StructuredLogger(logging.LoggerAdapter):
    """Logger adapter that supports structured logging"""

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """Process log message and add extra fields"""
        extra = kwargs.get("extra", {})

        # Store extra fields in record
        if extra:
            kwargs["extra"] = {"extra_fields": extra}

        return msg, kwargs


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """
    Setup application logging

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON formatter (True) or simple text (False)
    """

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter
    if json_format:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        StructuredLogger instance
    """
    base_logger = logging.getLogger(name)
    return StructuredLogger(base_logger, {})


# Usage example:
"""
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("User created successfully")

# Log with context
logger.info(
    "User created successfully",
    extra={
        "user_id": str(user.id),
        "user_email": user.email,
        "action": "user_creation"
    }
)

# Log with exception
try:
    process_image()
except Exception as e:
    logger.error(
        "Failed to process image",
        exc_info=True,
        extra={
            "image_url": image_url,
            "user_id": str(user_id)
        }
    )

Output JSON:
{
    "timestamp": "2025-11-11T10:30:00.123456",
    "level": "INFO",
    "logger": "app.services.user_service",
    "message": "User created successfully",
    "module": "user_service",
    "function": "create_user",
    "line": 45,
    "request_id": "abc-123-def",
    "user_id": "uuid-456",
    "context": {
        "user_id": "uuid-456",
        "user_email": "test@example.com",
        "action": "user_creation"
    }
}
"""

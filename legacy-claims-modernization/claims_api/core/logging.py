"""Structured JSON logging configuration."""

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

# Context variable for correlation ID
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID, generate if not provided."""
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    return correlation_id


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if present
        correlation_id = get_correlation_id()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging."""
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create JSON handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Set level for our application logger
    app_logger = logging.getLogger("claims_api")
    app_logger.setLevel(log_level)

    # Reduce noise from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(f"claims_api.{name}")

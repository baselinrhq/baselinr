"""
Structured JSON logging for Baselinr.

Provides consistent structured logging across all components with
run context propagation and event bus integration.
"""

import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


@dataclass
class RunContext:
    """
    Run context for propagating run_id and logger throughout the pipeline.

    Attributes:
        run_id: Unique identifier for this profiling run
        logger: Structured logger instance
        component: Component name (cli, profile_engine, etc.)
        metrics_enabled: Whether Prometheus metrics are enabled
    """

    run_id: str
    logger: Any
    component: str = "baselinr"
    metrics_enabled: bool = False

    @classmethod
    def create(
        cls,
        component: str = "baselinr",
        run_id: Optional[str] = None,
        metrics_enabled: bool = False,
    ) -> "RunContext":
        """
        Create a new run context with a fresh run_id and logger.

        Args:
            component: Component name
            run_id: Optional run_id (generates new one if not provided)
            metrics_enabled: Whether Prometheus metrics are enabled

        Returns:
            RunContext instance
        """
        if run_id is None:
            run_id = str(uuid.uuid4())

        logger = get_logger(component=component, run_id=run_id)
        return cls(
            run_id=run_id, logger=logger, component=component, metrics_enabled=metrics_enabled
        )


def init_logging(run_id: str, component: str = "baselinr", level: str = "INFO") -> Any:
    """
    Initialize structured JSON logging for Baselinr.

    Args:
        run_id: Unique run identifier to attach to all logs
        component: Component name (cli, profile_engine, warehouse_connector, drift_detector)
        level: Log level (INFO, DEBUG, ERROR)

    Returns:
        Configured logger instance
    """
    if STRUCTLOG_AVAILABLE:
        return _init_structlog(run_id, component, level)
    else:
        return _init_stdlib_logging(run_id, component, level)


def _init_structlog(run_id: str, component: str, level: str) -> Any:
    """Initialize structlog with JSON output."""

    # Convert string level to numeric
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )

    # Get logger and bind run context
    logger = structlog.get_logger()
    logger = logger.bind(run_id=run_id, component=component)

    return logger


def _init_stdlib_logging(run_id: str, component: str, level: str) -> Any:
    """Fallback to stdlib logging with JSON-like format if structlog not available."""

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger(f"baselinr.{component}")
    logger.setLevel(numeric_level)

    # Clear existing handlers
    logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    # JSON-like format
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        f'"run_id": "{run_id}", "component": "{component}", '
        '"message": "%(message)s"}'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    # Mark it as stdlib logger so we can detect it
    logger._is_stdlib = True  # type: ignore[attr-defined]

    return logger


def get_logger(component: str = "baselinr", run_id: Optional[str] = None) -> Any:
    """
    Get a logger instance for a specific component.

    Args:
        component: Component name
        run_id: Optional run_id to bind

    Returns:
        Logger instance
    """
    if STRUCTLOG_AVAILABLE:
        logger = structlog.get_logger()
        logger = logger.bind(component=component)
        if run_id:
            logger = logger.bind(run_id=run_id)
        return logger
    else:
        logger = logging.getLogger(f"baselinr.{component}")
        return logger


def log_event(
    logger: Any,
    event_type: str,
    message: str,
    level: str = "info",
    table: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Log a structured event.

    Args:
        logger: Logger instance
        event_type: Type of event (profiling_started, drift_detected, etc.)
        message: Human-readable message
        level: Log level (info, error, debug)
        table: Optional table name (schema.table)
        metadata: Optional metadata dictionary
    """
    log_func = getattr(logger, level.lower(), logger.info)

    kwargs = {
        "event_type": event_type,
    }

    if table:
        kwargs["table"] = table

    if metadata:
        kwargs["metadata"] = metadata  # type: ignore[assignment]

    # Check if this is a structlog logger (has bind method) or our stdlib logger
    is_structlog = hasattr(logger, "bind")
    is_stdlib_logger = hasattr(logger, "_is_stdlib") or isinstance(logger, logging.Logger)

    if is_structlog and not is_stdlib_logger:
        # Use structlog's keyword argument support
        log_func(message, **kwargs)
    else:
        # For stdlib logging, format as string
        extra_info = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        log_func(f"{message} [{extra_info}]")


def log_and_emit(
    logger: Any,
    event_bus: Optional[Any],
    event_type: str,
    message: str,
    level: str = "info",
    table: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Dual-write: log an event AND emit it to the event bus.

    This ensures logs and event streams stay synchronized.

    Args:
        logger: Logger instance
        event_bus: Event bus instance (optional)
        event_type: Type of event
        message: Human-readable message
        level: Log level
        table: Optional table name
        run_id: Optional run_id
        metadata: Optional metadata
    """
    # Log the event
    log_event(logger, event_type, message, level, table, metadata)

    # Emit to event bus if available
    if event_bus:
        from ..events import BaseEvent

        # Build event metadata
        event_metadata = metadata.copy() if metadata else {}
        if run_id:
            event_metadata["run_id"] = run_id
        if table:
            event_metadata["table"] = table
        event_metadata["message"] = message

        # Create BaseEvent object
        event = BaseEvent(
            event_type=event_type, timestamp=datetime.utcnow(), metadata=event_metadata
        )

        try:
            event_bus.emit(event)
        except Exception as e:
            # Use string formatting for error to avoid kwargs issue with stdlib logging
            is_structlog = hasattr(logger, "bind")
            is_stdlib_logger = hasattr(logger, "_is_stdlib") or isinstance(logger, logging.Logger)

            if is_structlog and not is_stdlib_logger:
                logger.error("Failed to publish event to event bus", error=str(e))
            else:
                logger.error(f"Failed to publish event to event bus: {e}")

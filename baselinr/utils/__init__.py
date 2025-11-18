"""
Utility modules for Baselinr.
"""

from .logging import (
    RunContext,
    get_logger,
    init_logging,
    log_and_emit,
    log_event,
)
from .metrics import (
    get_warehouse_type,
    is_metrics_enabled,
    record_drift_detection_completed,
    record_drift_event,
    record_error,
    record_profile_completed,
    record_profile_failed,
    record_profile_started,
    record_query_completed,
    record_schema_change,
    start_metrics_server,
)
from .retry import (
    ConnectionLostError,
    PermanentWarehouseError,
    RateLimitError,
    TimeoutError,
    TransientWarehouseError,
    retry_with_backoff,
    retryable_call,
)

__all__ = [
    # Retry utilities
    "retry_with_backoff",
    "retryable_call",
    "TransientWarehouseError",
    "PermanentWarehouseError",
    "TimeoutError",
    "ConnectionLostError",
    "RateLimitError",
    # Logging utilities
    "RunContext",
    "init_logging",
    "get_logger",
    "log_event",
    "log_and_emit",
    # Metrics utilities
    "record_profile_started",
    "record_profile_completed",
    "record_profile_failed",
    "record_drift_event",
    "record_drift_detection_completed",
    "record_schema_change",
    "record_error",
    "record_query_completed",
    "start_metrics_server",
    "is_metrics_enabled",
    "get_warehouse_type",
]

"""
Utility modules for ProfileMesh.
"""

from .retry import (
    retry_with_backoff,
    retryable_call,
    TransientWarehouseError,
    PermanentWarehouseError,
    TimeoutError,
    ConnectionLostError,
    RateLimitError,
)
from .logging import (
    RunContext,
    init_logging,
    get_logger,
    log_event,
    log_and_emit,
)
from .metrics import (
    record_profile_started,
    record_profile_completed,
    record_profile_failed,
    record_drift_event,
    record_drift_detection_completed,
    record_schema_change,
    record_error,
    record_query_completed,
    start_metrics_server,
    is_metrics_enabled,
    get_warehouse_type,
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


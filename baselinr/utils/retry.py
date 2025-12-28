"""
Retry and recovery utilities for Baselinr.

Provides robust retry logic with exponential backoff for transient warehouse errors.
Integrates with structured logging, event bus, and Prometheus metrics.
"""

import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

try:
    from prometheus_client import Counter
except ImportError:
    Counter = None  # type: ignore[assignment, misc]

try:
    from .metrics import is_metrics_enabled
except ImportError:

    def is_metrics_enabled() -> bool:
        return False


logger = logging.getLogger(__name__)
event_bus = None  # Optional event bus injected at runtime or during tests


# ============================================================
# Error Taxonomy
# ============================================================


class TransientWarehouseError(Exception):
    """Base class for transient warehouse errors that should be retried."""

    pass


class PermanentWarehouseError(Exception):
    """Base class for permanent warehouse errors that should not be retried."""

    pass


class TimeoutError(TransientWarehouseError):
    """Warehouse query timeout error."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)


class ConnectionLostError(TransientWarehouseError):
    """Database connection lost error."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)


class RateLimitError(TransientWarehouseError):
    """API rate limit exceeded error."""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)


# ============================================================
# Retry Decorator
# ============================================================


def retry_with_backoff(
    retries: int = 3,
    backoff_strategy: str = "exponential",
    min_backoff: float = 0.5,
    max_backoff: float = 8.0,
    retry_on: Tuple[Type[Exception], ...] = (TransientWarehouseError,),
):
    """
    Decorator that retries a function with exponential backoff on transient errors.

    Args:
        retries: Maximum number of retry attempts
        backoff_strategy: "exponential" or "fixed" backoff strategy
        min_backoff: Minimum backoff delay in seconds
        max_backoff: Maximum backoff delay in seconds
        retry_on: Tuple of exception types to retry on

    Returns:
        Decorated function that implements retry logic

    Example:
        @retry_with_backoff(retries=3, backoff_strategy="exponential")
        def query_warehouse(sql):
            # This will be retried up to 3 times on TransientWarehouseError
            return execute_sql(sql)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(retries + 1):
                try:
                    # Attempt to execute the function
                    result = func(*args, **kwargs)

                    # If we retried and succeeded, log success
                    if attempt > 0:
                        _log_retry_success(func.__name__, attempt)

                    return result

                except Exception as e:
                    # Check if this is a retryable error
                    if not isinstance(e, retry_on):
                        # Not a retryable error, re-raise immediately
                        raise

                    last_exception = e

                    # If we've exhausted retries, re-raise
                    if attempt >= retries:
                        _log_retry_exhausted(func.__name__, attempt + 1, e)
                        _emit_retry_failure(func.__name__, e)
                        raise

                    # Calculate backoff delay
                    if backoff_strategy == "exponential":
                        sleep_time = min(max_backoff, min_backoff * (2**attempt))
                        # Add jitter (up to 15% of sleep time)
                        sleep_time += random.uniform(0, sleep_time * 0.15)
                    else:  # fixed
                        sleep_time = min_backoff

                    # Log the retry attempt
                    _log_retry_attempt(func.__name__, attempt + 1, retries, e, sleep_time)

                    # Emit event and metrics
                    _emit_retry_event(func.__name__, attempt + 1, e)
                    _record_retry_metric()

                    # Sleep before retry
                    time.sleep(sleep_time)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retryable_call(
    fn: Callable,
    *args,
    retries: int = 3,
    backoff_strategy: str = "exponential",
    min_backoff: float = 0.5,
    max_backoff: float = 8.0,
    retry_on: Tuple[Type[Exception], ...] = (TransientWarehouseError,),
    **kwargs,
) -> Any:
    """
    Function wrapper version of retry_with_backoff for dynamic invocation.

    Args:
        fn: Function to call
        *args: Positional arguments to pass to fn
        retries: Maximum number of retry attempts
        backoff_strategy: "exponential" or "fixed" backoff strategy
        min_backoff: Minimum backoff delay in seconds
        max_backoff: Maximum backoff delay in seconds
        retry_on: Tuple of exception types to retry on
        **kwargs: Keyword arguments to pass to fn

    Returns:
        Result of fn(*args, **kwargs)

    Example:
        result = retryable_call(
            query_warehouse,
            "SELECT * FROM table",
            retries=3,
            retry_on=(TimeoutError,)
        )
    """
    decorated_fn = retry_with_backoff(
        retries=retries,
        backoff_strategy=backoff_strategy,
        min_backoff=min_backoff,
        max_backoff=max_backoff,
        retry_on=retry_on,
    )(fn)

    return decorated_fn(*args, **kwargs)


# ============================================================
# Helper Functions
# ============================================================


def _log_retry_attempt(
    func_name: str, attempt: int, max_retries: int, error: Exception, sleep_time: float
):
    """Log a retry attempt with structured logging."""
    try:
        from .logging import get_logger, log_event

        retry_logger = get_logger(__name__)

        log_event(
            retry_logger,
            "retry_attempt",
            f"Retry attempt {attempt}/{max_retries} for {func_name} after "
            f"{type(error).__name__}: {error}",
            level="warning",
            metadata={
                "function": func_name,
                "attempt": attempt,
                "max_retries": max_retries,
                "error": str(error),
                "error_type": type(error).__name__,
                "backoff_seconds": sleep_time,
            },
        )
    except ImportError:
        # Fallback to standard logging if structured logging not available
        logger.warning(
            f"Retry attempt {attempt}/{max_retries} for {func_name}: "
            f"{type(error).__name__}: {error} (backing off {sleep_time:.2f}s)"
        )


def _log_retry_success(func_name: str, attempts: int):
    """Log successful retry."""
    try:
        from .logging import get_logger, log_event

        retry_logger = get_logger(__name__)

        log_event(
            retry_logger,
            "retry_success",
            f"Function {func_name} succeeded after {attempts} retry attempts",
            level="info",
            metadata={"function": func_name, "total_attempts": attempts + 1},
        )
    except ImportError:
        logger.info(f"Function {func_name} succeeded after {attempts} retry attempts")


def _log_retry_exhausted(func_name: str, total_attempts: int, error: Exception):
    """Log retry exhaustion."""
    try:
        from .logging import get_logger, log_event

        retry_logger = get_logger(__name__)

        log_event(
            retry_logger,
            "retry_exhausted",
            f"All {total_attempts} retry attempts exhausted for {func_name}: {error}",
            level="error",
            metadata={
                "function": func_name,
                "total_attempts": total_attempts,
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )
    except ImportError:
        logger.error(
            f"All {total_attempts} retry attempts exhausted for {func_name}: "
            f"{type(error).__name__}: {error}"
        )


def _emit_retry_event(func_name: str, attempt: int, error: Exception):
    """Emit retry event to event bus."""
    global event_bus  # noqa: F824
    if event_bus is None:
        return
    try:
        from datetime import datetime, timezone

        from ..events.events import BaseEvent

        event = BaseEvent(
            event_type="retry_attempt",
            timestamp=datetime.now(timezone.utc),
            metadata={
                "function": func_name,
                "attempt": attempt,
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )

        event_bus.emit(event)
    except Exception as e:
        logger.debug(f"Could not emit retry event: {e}")


def _emit_retry_failure(func_name: str, error: Exception):
    """Emit retry failure event to event bus."""
    global event_bus  # noqa: F824
    if event_bus is None:
        return
    try:
        from datetime import datetime, timezone

        from ..events.events import BaseEvent

        event = BaseEvent(
            event_type="retry_exhausted",
            timestamp=datetime.now(timezone.utc),
            metadata={
                "function": func_name,
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )

        event_bus.emit(event)
    except Exception as e:
        logger.debug(f"Could not emit retry failure event: {e}")


def _record_retry_metric():
    """Record retry metric in Prometheus."""
    if Counter is None:
        return
    try:
        if is_metrics_enabled():
            transient_errors_counter = Counter(
                "baselinr_warehouse_transient_errors_total",
                "Total number of transient warehouse errors encountered",
            )
            transient_errors_counter.inc()
    except (ImportError, Exception) as e:
        logger.debug(f"Could not record retry metric: {e}")


# ============================================================
# Exception Classifier
# ============================================================


def classify_database_error(exception: Exception) -> Exception:
    """
    Classify a database exception as transient or permanent.

    Converts native database errors into standardized Baselinr error types.

    Args:
        exception: The original database exception

    Returns:
        Classified exception (TransientWarehouseError or PermanentWarehouseError)

    Example:
        try:
            execute_query(sql)
        except Exception as e:
            raise classify_database_error(e)
    """
    # Safely extract error string to avoid DBAPIError reconstruction issues
    # Use args[0] if available, otherwise try str(), otherwise use type name
    try:
        if hasattr(exception, "args") and exception.args and len(exception.args) > 0:
            error_str = str(exception.args[0]).lower()
            error_message = str(exception.args[0])
        else:
            error_str = str(exception).lower()
            error_message = str(exception)
    except Exception:
        try:
            exception_type_name = type(exception).__name__
            error_str = f"exception of type {exception_type_name}".lower()
            error_message = f"Exception of type {exception_type_name}"
        except Exception:
            error_str = "unknown error"
            error_message = "Unknown error"

    try:
        exception_type = type(exception).__name__.lower()
    except Exception:
        exception_type = "exception"

    # Common transient error patterns
    transient_patterns = [
        "timeout",
        "connection reset",
        "connection lost",
        "connection refused",
        "broken pipe",
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "deadlock",
        "lock timeout",
        "could not obtain lock",
        "connection pool exhausted",
        "connection closed",
        "network error",
        "i/o error",
        "communication link failure",
    ]

    # Check if error matches transient patterns
    for pattern in transient_patterns:
        if pattern in error_str or pattern in exception_type:
            # Determine specific transient error type
            if "timeout" in error_str or "timeout" in exception_type:
                return TimeoutError(error_message)
            elif "rate limit" in error_str or "too many" in error_str:
                return RateLimitError(error_message)
            elif any(p in error_str for p in ["connection", "network", "communication"]):
                return ConnectionLostError(error_message)
            else:
                return TransientWarehouseError(error_message)

    # Default to permanent error
    return PermanentWarehouseError(error_message)

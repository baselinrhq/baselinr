"""
Prometheus metrics exporter for Baselinr.

This module provides Prometheus-compliant metrics for monitoring:
- Profiling runs and latency
- Drift detection events
- Warehouse errors
- Worker activity
"""

import logging
from typing import Any, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Create stub classes when prometheus_client is not available
    class _StubMetric:
        """Stub metric class when prometheus_client is not available."""

        def __init__(self, *args, **kwargs):
            """Accept any arguments but do nothing."""
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, value=1):
            pass

        def dec(self, value=1):
            pass

        def observe(self, value):
            pass

        def set(self, value):
            pass

    Counter = _StubMetric  # type: ignore[assignment, misc]
    Histogram = _StubMetric  # type: ignore[assignment, misc]
    Gauge = _StubMetric  # type: ignore[assignment, misc]

    def start_http_server(port: int) -> Any:  # type: ignore[misc]
        """Stub function when prometheus_client is not available."""
        logger.warning("prometheus_client not available, metrics server not started")


logger = logging.getLogger(__name__)


# ============================================================
# Metric Definitions
# ============================================================

profile_runs_total = Counter(
    "baselinr_profile_runs_total",
    "Total number of profiling runs",
    ["warehouse", "table", "status"],
)

drift_events_total = Counter(
    "baselinr_drift_events_total",
    "Total number of drift detection events",
    ["warehouse", "table", "metric", "severity"],
)

schema_changes_total = Counter(
    "baselinr_schema_changes_total",
    "Total number of schema change events",
    ["warehouse", "table", "change_type"],
)

errors_total = Counter(
    "baselinr_errors_total", "Total number of errors", ["warehouse", "error_type", "component"]
)

profile_duration_seconds = Histogram(
    "baselinr_profile_duration_seconds",
    "Histogram of profile execution times in seconds",
    ["warehouse", "table"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

drift_detection_duration_seconds = Histogram(
    "baselinr_drift_detection_duration_seconds",
    "Histogram of drift detection execution times in seconds",
    ["warehouse", "table"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

query_duration_seconds = Histogram(
    "baselinr_query_duration_seconds",
    "Histogram of warehouse query execution times in seconds",
    ["warehouse"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
)

active_workers = Gauge(
    "baselinr_active_workers", "Number of currently running worker threads", ["warehouse"]
)

worker_tasks_total = Counter(
    "baselinr_worker_tasks_total",
    "Total number of worker tasks",
    ["warehouse", "status"],  # status: started, completed, failed
)

worker_queue_size = Gauge(
    "baselinr_worker_queue_size", "Current size of worker task queue", ["warehouse"]
)

batch_duration_seconds = Histogram(
    "baselinr_batch_duration_seconds",
    "Histogram of batch execution times",
    ["warehouse", "batch_size"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

rows_profiled_total = Counter(
    "baselinr_rows_profiled_total", "Total number of rows profiled", ["warehouse", "table"]
)

columns_profiled_total = Counter(
    "baselinr_columns_profiled_total", "Total number of columns profiled", ["warehouse", "table"]
)


# ============================================================
# Metric Recording Functions
# ============================================================


def record_profile_started(warehouse: str, table: str):
    """
    Record the start of a profiling operation.

    Args:
        warehouse: Warehouse type (postgres, snowflake, etc.)
        table: Fully qualified table name
    """
    active_workers.labels(warehouse=warehouse).inc()
    logger.debug(f"Metrics: Profile started for {warehouse}/{table}")


def record_profile_completed(
    warehouse: str,
    table: str,
    duration_seconds: float,
    row_count: Optional[int] = None,
    column_count: Optional[int] = None,
):
    """
    Record the completion of a profiling operation.

    Args:
        warehouse: Warehouse type
        table: Fully qualified table name
        duration_seconds: Time taken for profiling
        row_count: Optional number of rows profiled
        column_count: Optional number of columns profiled
    """
    profile_runs_total.labels(warehouse, table, "success").inc()
    profile_duration_seconds.labels(warehouse, table).observe(duration_seconds)
    active_workers.labels(warehouse=warehouse).dec()

    if row_count is not None:
        rows_profiled_total.labels(warehouse, table).inc(row_count)

    if column_count is not None:
        columns_profiled_total.labels(warehouse, table).inc(column_count)

    logger.debug(f"Metrics: Profile completed for {warehouse}/{table} in {duration_seconds:.2f}s")


def record_profile_failed(warehouse: str, table: str, duration_seconds: float):
    """
    Record a failed profiling operation.

    Args:
        warehouse: Warehouse type
        table: Fully qualified table name
        duration_seconds: Time taken before failure
    """
    profile_runs_total.labels(warehouse, table, "failed").inc()
    profile_duration_seconds.labels(warehouse, table).observe(duration_seconds)
    active_workers.labels(warehouse=warehouse).dec()

    logger.debug(f"Metrics: Profile failed for {warehouse}/{table} after {duration_seconds:.2f}s")


def record_drift_event(warehouse: str, table: str, metric: str, severity: str = "unknown"):
    """
    Record a drift detection event.

    Args:
        warehouse: Warehouse type
        table: Table name
        metric: Metric name that drifted
        severity: Drift severity (low, medium, high)
    """
    drift_events_total.labels(warehouse, table, metric, severity).inc()
    logger.debug(
        f"Metrics: Drift detected in {warehouse}/{table} metric={metric} severity={severity}"
    )


def record_drift_detection_completed(warehouse: str, table: str, duration_seconds: float):
    """
    Record drift detection completion.

    Args:
        warehouse: Warehouse type
        table: Table name
        duration_seconds: Time taken for drift detection
    """
    drift_detection_duration_seconds.labels(warehouse, table).observe(duration_seconds)
    logger.debug(
        f"Metrics: Drift detection completed for {warehouse}/{table} in {duration_seconds:.2f}s"
    )


def record_schema_change(warehouse: str, table: str, change_type: str):
    """
    Record a schema change event.

    Args:
        warehouse: Warehouse type
        table: Table name
        change_type: Type of change (column_added, column_removed, type_changed)
    """
    schema_changes_total.labels(warehouse, table, change_type).inc()
    logger.debug(f"Metrics: Schema change in {warehouse}/{table} type={change_type}")


def record_error(warehouse: str, error_type: str, component: str = "unknown"):
    """
    Record an error event.

    Args:
        warehouse: Warehouse type
        error_type: Type of error (e.g., ConnectionError, TimeoutError)
        component: Component where error occurred (profiler, drift_detector, etc.)
    """
    errors_total.labels(warehouse, error_type, component).inc()
    logger.debug(f"Metrics: Error in {component} warehouse={warehouse} type={error_type}")


def record_query_completed(warehouse: str, duration_seconds: float):
    """
    Record a warehouse query completion.

    Args:
        warehouse: Warehouse type
        duration_seconds: Time taken for query
    """
    query_duration_seconds.labels(warehouse).observe(duration_seconds)
    logger.debug(f"Metrics: Query completed for {warehouse} in {duration_seconds:.2f}s")


# ============================================================
# Metrics Server
# ============================================================

_metrics_server_started = False


def start_metrics_server(port: int = 9753):
    """
    Start a Prometheus metrics HTTP endpoint at /metrics.

    Args:
        port: Port to listen on (default: 9753)

    Note:
        This starts a background HTTP server that exposes metrics
        at http://localhost:<port>/metrics
    """
    global _metrics_server_started

    if _metrics_server_started:
        logger.warning("Metrics server already started, skipping")
        return

    try:
        start_http_server(port)
        _metrics_server_started = True
        logger.info(f"Prometheus metrics server started on port {port}")
        logger.info(f"Metrics available at http://localhost:{port}/metrics")
    except OSError as e:
        logger.error(f"Failed to start metrics server on port {port}: {e}")
        raise


def is_metrics_enabled() -> bool:
    """
    Check if metrics server is running.

    Returns:
        True if metrics server is started
    """
    return _metrics_server_started


# ============================================================
# Utility Functions
# ============================================================


def get_warehouse_type(config) -> str:
    """
    Extract warehouse type from connection config.

    Args:
        config: Connection configuration object

    Returns:
        Warehouse type string (postgres, snowflake, etc.)
    """
    if hasattr(config, "type"):
        return config.type  # type: ignore[no-any-return]
    elif hasattr(config, "connection") and hasattr(config.connection, "type"):
        return config.connection.type  # type: ignore[no-any-return]
    else:
        return "unknown"

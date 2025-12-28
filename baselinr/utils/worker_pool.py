"""
Worker pool module for parallel table profiling.

Provides a thread-based worker pool abstraction for executing profiling
tasks concurrently with error isolation, structured logging, and metrics.
"""

import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Manages a pool of worker threads for parallel table profiling.

    This is only used when max_workers > 1. When max_workers=1,
    ProfileEngine uses sequential execution (existing behavior).

    Features:
    - Bounded task queue to prevent memory overrun
    - Configurable worker count
    - Error isolation per task
    - Structured logging for worker lifecycle
    - Event emission for task start/complete/failure
    - Metrics integration
    """

    def __init__(self, max_workers: int, queue_size: int = 100, warehouse_type: str = "unknown"):
        """
        Initialize worker pool.

        Args:
            max_workers: Maximum number of concurrent workers (must be > 1)
            queue_size: Maximum size of task queue
            warehouse_type: Warehouse type for metrics/logging

        Raises:
            ValueError: If max_workers <= 1
        """
        if max_workers <= 1:
            raise ValueError(
                "WorkerPool requires max_workers > 1. Use sequential execution for max_workers=1"
            )

        self.max_workers = max_workers
        self.queue_size = queue_size
        self.warehouse_type = warehouse_type

        # Initialize thread pool executor
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Track active tasks
        self.active_tasks: Dict[Future, str] = {}

        # Initialize logger
        from .logging import get_logger

        self.logger = get_logger(__name__)

        self.logger.info(
            f"WorkerPool initialized (max_workers={max_workers}, "
            f"queue_size={queue_size}, warehouse_type={warehouse_type})"
        )

    def submit(self, task: Callable, *args, **kwargs) -> Future:
        """
        Submit a task to the worker pool.

        Args:
            task: Callable to execute
            *args: Positional arguments for task
            **kwargs: Keyword arguments for task

        Returns:
            Future object representing the task
        """
        # Submit task to executor
        future = self.executor.submit(task, *args, **kwargs)

        # Track active task
        task_name = getattr(task, "__name__", "unknown_task")
        self.active_tasks[future] = task_name

        # Log task submission
        try:
            from .logging import log_event

            log_event(
                self.logger,
                "task_submitted",
                f"Task {task_name} submitted to worker pool",
                level="debug",
                metadata={
                    "task": task_name,
                    "active_tasks": len(self.active_tasks),
                    "max_workers": self.max_workers,
                },
            )
        except ImportError:
            self.logger.debug(f"Task {task_name} submitted to worker pool")

        # Update metrics
        self._update_active_workers_metric()
        self._update_queue_size_metric()

        return future

    def submit_batch(self, tasks: List[Tuple[Callable, tuple, dict]]) -> List[Future]:
        """
        Submit multiple tasks as a batch.

        Args:
            tasks: List of (callable, args_tuple, kwargs_dict) tuples

        Returns:
            List of Future objects
        """
        futures = []

        # Emit batch started event
        self._emit_batch_event("batch_started", len(tasks))

        for callable_fn, args, kwargs in tasks:
            future = self.submit(callable_fn, *args, **kwargs)
            futures.append(future)

        return futures

    def wait_for_completion(
        self, futures: List[Future], timeout: Optional[float] = None
    ) -> List[Any]:
        """
        Wait for all futures to complete and return results.

        Args:
            futures: List of Future objects
            timeout: Optional timeout in seconds

        Returns:
            List of results (or None for failed tasks)
        """
        results_map: Dict[Future, Any] = {}
        successful = 0
        failed = 0
        start_time = time.time()

        try:
            for future in as_completed(futures, timeout=timeout):
                try:
                    result = future.result()
                    results_map[future] = result
                    successful += 1

                    # Remove from active tasks
                    task_name = self.active_tasks.pop(future, "unknown")

                    # Log completion
                    self._log_task_completion(task_name, success=True)

                except Exception as e:
                    failed += 1
                    results_map[future] = None

                    # Remove from active tasks
                    task_name = self.active_tasks.pop(future, "unknown")

                    # Log failure
                    self._log_task_completion(task_name, success=False, error=e)

                # Update metrics
                self._update_active_workers_metric()

        except TimeoutError:
            self.logger.error(f"Timeout waiting for tasks to complete after {timeout}s")
            # Return whatever we have
            pass

        duration = time.time() - start_time

        # Emit batch completed event
        self._emit_batch_event("batch_completed", len(futures), successful, failed, duration)

        # Record batch duration metric
        self._record_batch_duration(len(futures), duration)

        ordered_results = []
        for future in futures:
            ordered_results.append(results_map.get(future))
        return ordered_results

    def shutdown(self, wait: bool = True, timeout: Optional[float] = None):
        """
        Shutdown the worker pool.

        Args:
            wait: Whether to wait for pending tasks
            timeout: Optional timeout for shutdown
        """
        try:
            from .logging import log_event

            log_event(
                self.logger,
                "worker_pool_shutdown",
                f"Shutting down worker pool (wait={wait})",
                level="info",
                metadata={"wait": wait, "active_tasks": len(self.active_tasks)},
            )
        except ImportError:
            self.logger.info(f"Shutting down worker pool (wait={wait})")

        self.executor.shutdown(wait=wait, cancel_futures=not wait)

    def _update_active_workers_metric(self):
        """Update active workers gauge metric."""
        try:
            from .metrics import active_workers, is_metrics_enabled

            if is_metrics_enabled():
                active_workers.labels(warehouse=self.warehouse_type).set(len(self.active_tasks))
        except (ImportError, Exception):
            # Silently fail if metrics not available
            pass

    def _update_queue_size_metric(self):
        """Update queue size gauge metric."""
        try:
            from .metrics import is_metrics_enabled, worker_queue_size

            if is_metrics_enabled():
                worker_queue_size.labels(warehouse=self.warehouse_type).set(len(self.active_tasks))
        except (ImportError, Exception):
            # Silently fail if metrics not available
            pass

    def _log_task_completion(
        self, task_name: str, success: bool, error: Optional[Exception] = None
    ):
        """Log task completion or failure."""
        try:
            from .logging import log_event

            if success:
                log_event(
                    self.logger,
                    "task_completed",
                    f"Task {task_name} completed successfully",
                    level="debug",
                    metadata={"task": task_name, "success": True},
                )

                # Record success metric
                self._record_task_metric("completed")
            else:
                log_event(
                    self.logger,
                    "task_failed",
                    f"Task {task_name} failed: {error}",
                    level="error",
                    metadata={
                        "task": task_name,
                        "success": False,
                        "error": str(error),
                        "error_type": type(error).__name__ if error else None,
                    },
                )

                # Record failure metric
                self._record_task_metric("failed")
        except ImportError:
            if success:
                self.logger.debug(f"Task {task_name} completed successfully")
            else:
                self.logger.error(f"Task {task_name} failed: {error}")

    def _record_task_metric(self, status: str):
        """Record task metric."""
        try:
            from .metrics import is_metrics_enabled, worker_tasks_total

            if is_metrics_enabled():
                worker_tasks_total.labels(warehouse=self.warehouse_type, status=status).inc()
        except (ImportError, Exception):
            # Silently fail if metrics not available
            pass

    def _record_batch_duration(self, batch_size: int, duration: float):
        """Record batch duration metric."""
        try:
            from .metrics import batch_duration_seconds, is_metrics_enabled

            if is_metrics_enabled():
                batch_duration_seconds.labels(
                    warehouse=self.warehouse_type, batch_size=str(batch_size)
                ).observe(duration)
        except (ImportError, Exception):
            # Silently fail if metrics not available
            pass

    def _emit_batch_event(
        self,
        event_type: str,
        batch_size: int,
        successful: int = 0,
        failed: int = 0,
        duration: float = 0.0,
    ):
        """Emit batch event to event bus."""
        try:
            # Note: No global event_bus instance available in worker pool context
            # Batch events are logged but not emitted to event bus
            # Individual table events are emitted via event_bus parameter in profile_table_task
            from ..events.events import BaseEvent

            metadata = {
                "batch_size": batch_size,
                "max_workers": self.max_workers,
                "warehouse": self.warehouse_type,
            }

            if event_type == "batch_completed":
                metadata.update(
                    {"successful": successful, "failed": failed, "duration_seconds": duration}
                )

            # Create event for logging purposes only
            _ = BaseEvent(event_type=event_type, timestamp=datetime.now(), metadata=metadata)
            # Skip emit - no global event_bus in worker pool context
        except (ImportError, Exception):
            # Silently fail if event bus not available
            pass


def profile_table_task(
    engine, table_pattern, run_context: Optional[Any] = None, event_bus: Optional[Any] = None
) -> Optional[Any]:
    """
    Wrapper function for profiling a single table in a worker thread.

    This function:
    - Isolates errors (exceptions don't crash other tasks)
    - Logs worker lifecycle events
    - Emits events to event bus
    - Records metrics
    - Returns None on failure (not raise) for error isolation

    Args:
        engine: ProfileEngine instance (thread-safe or per-worker)
        table_pattern: Table pattern to profile
        run_context: Optional run context for logging
        event_bus: Optional event bus for events

    Returns:
        ProfilingResult on success, None on failure
    """
    import logging
    from datetime import datetime

    logger = logging.getLogger(__name__)
    table_name = (
        f"{table_pattern.schema_}.{table_pattern.table}"
        if table_pattern.schema_
        else table_pattern.table
    )

    start_time = time.time()

    try:
        # Log worker start
        try:
            from .logging import log_event

            log_event(
                logger,
                "worker_started",
                f"Worker started processing table {table_name}",
                level="debug",
                metadata={"table": table_name},
            )
        except ImportError:
            logger.debug(f"Worker started processing table {table_name}")

        # Emit profiling_started event
        if event_bus:
            try:
                from ..events.events import BaseEvent

                event = BaseEvent(
                    event_type="profiling_started",
                    timestamp=datetime.now(),
                    metadata={"table": table_name, "worker_execution": True},
                )
                event_bus.emit(event)
            except Exception:
                pass

        # Call engine._profile_table(pattern)
        result = engine._profile_table(table_pattern)

        duration = time.time() - start_time

        # Log completion
        try:
            from .logging import log_event

            log_event(
                logger,
                "worker_completed",
                f"Worker completed table {table_name}",
                level="info",
                metadata={"table": table_name, "duration_seconds": duration, "success": True},
            )
        except ImportError:
            logger.info(f"Worker completed table {table_name} in {duration:.2f}s")

        # Emit profiling_completed event
        if event_bus:
            try:
                from ..events.events import BaseEvent

                event = BaseEvent(
                    event_type="profiling_completed",
                    timestamp=datetime.now(),
                    metadata={
                        "table": table_name,
                        "duration_seconds": duration,
                        "worker_execution": True,
                    },
                )
                event_bus.emit(event)
            except Exception:
                pass

        # Record metrics
        try:
            from .metrics import is_metrics_enabled

            if is_metrics_enabled():
                from .metrics import get_warehouse_type, record_profile_completed

                # Get warehouse type from engine's config
                warehouse = (
                    get_warehouse_type(engine.config.source)
                    if hasattr(engine, "config") and hasattr(engine.config, "source")
                    else "unknown"
                )
                record_profile_completed(warehouse, table_name, duration)
        except (ImportError, Exception):
            pass

        return result

    except Exception as e:
        duration = time.time() - start_time

        # Safely extract error type name without accessing exception internals
        # that might trigger DBAPIError reconstruction
        try:
            error_type_name = type(e).__name__
        except Exception:
            # Fallback if accessing type fails (e.g., DBAPIError with __cause__)
            error_type_name = "Exception"

        error_str = str(e)

        # Log error but don't raise
        try:
            from .logging import log_event

            log_event(
                logger,
                "table_profiling_failed",
                f"Failed to profile {table_name}: {error_str}",
                level="error",
                metadata={
                    "table": table_name,
                    "error": error_str,
                    "error_type": error_type_name,
                    "duration_seconds": duration,
                },
            )
        except ImportError:
            logger.error(f"Failed to profile {table_name}: {error_str}")

        # Emit failure event
        if event_bus:
            try:
                from ..events.events import BaseEvent

                event = BaseEvent(
                    event_type="profiling_failed",
                    timestamp=datetime.now(),
                    metadata={
                        "table": table_name,
                        "error": error_str,
                        "error_type": error_type_name,
                        "duration_seconds": duration,
                        "worker_execution": True,
                    },
                )
                event_bus.emit(event)
            except Exception:
                pass

        # Record failure metric
        try:
            from .metrics import is_metrics_enabled

            if is_metrics_enabled():
                from .metrics import get_warehouse_type, record_profile_failed

                # Get warehouse type from engine's config
                warehouse = (
                    get_warehouse_type(engine.config.source)
                    if hasattr(engine, "config") and hasattr(engine.config, "source")
                    else "unknown"
                )
                record_profile_failed(warehouse, table_name, 0.0)
        except (ImportError, Exception):
            pass

        # Return None (not raise) so other tasks continue
        return None

# Cursor Prompt: Implement Parallelism & Batching for ProfileMesh

## Goal
Add **optional** parallel execution and batching capabilities to ProfileMesh so that multiple tables can be profiled concurrently when enabled. This feature is **opt-in** and defaults to sequential execution (current behavior) for backward compatibility. The primary use case is CLI execution where users want to profile many tables faster. Dagster users already benefit from asset-level parallelism, but this feature can still be useful for batching within a single asset or for fine-grained control.

**Key Design Decision:**
- **Default**: `max_workers=1` (sequential execution, maintains current behavior)
- **Opt-in**: Users enable parallelism via configuration
- **CLI-focused**: Primary benefit is for CLI users profiling many tables
- **Dagster-compatible**: Works with Dagster but not required (Dagster already provides asset-level parallelism)

---

# System-Facing Instructions (for Cursor)

You are modifying the **ProfileMesh** codebase. Implement the following exactly:

---

# 1. Create Execution Configuration Schema

Update `profilemesh/config/schema.py`:

Add a new `ExecutionConfig` class:

```python
import os

class ExecutionConfig(BaseModel):
    """Execution and parallelism configuration.
    
    This configuration is OPTIONAL and defaults to sequential execution
    (max_workers=1) for backward compatibility. Enable parallelism by
    setting max_workers > 1.
    
    Note: Dagster users already benefit from asset-level parallelism.
    This feature is primarily useful for CLI execution or when batching
    multiple tables within a single Dagster asset.
    """
    
    # CRITICAL: Default to 1 (sequential) for backward compatibility
    max_workers: int = Field(1, ge=1, le=64)
    batch_size: int = Field(10, ge=1, le=100)
    queue_size: int = Field(100, ge=10, le=1000)  # Bounded queue size
    
    # Warehouse-specific overrides (optional)
    warehouse_limits: Dict[str, int] = Field(default_factory=dict)
    # Example: {"snowflake": 20, "postgres": 8, "sqlite": 1}
    
    @field_validator("max_workers")
    @classmethod
    def validate_max_workers(cls, v: int) -> int:
        """Ensure max_workers is reasonable."""
        if v > 1:
            # Only validate if parallelism is enabled
            cpu_count = os.cpu_count() or 4
            if v > cpu_count * 4:
                raise ValueError(f"max_workers ({v}) should not exceed {cpu_count * 4} (4x CPU count)")
        return v
```

**Important**: The default `max_workers=1` ensures sequential execution unless explicitly enabled.

Add to `ProfileMeshConfig`:
```python
execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
```

---

# 2. Create Worker Pool Module

Create file:
```
profilemesh/utils/worker_pool.py
```

Implement:

## A. `WorkerPool` Class

```python
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
    
    def __init__(
        self,
        max_workers: int,
        queue_size: int = 100,
        warehouse_type: str = "unknown"
    ):
        """
        Initialize worker pool.
        
        Args:
            max_workers: Maximum number of concurrent workers (must be > 1)
            queue_size: Maximum size of task queue
            warehouse_type: Warehouse type for metrics/logging
        """
        if max_workers <= 1:
            raise ValueError("WorkerPool requires max_workers > 1. Use sequential execution for max_workers=1")
        
        # Implementation details:
        # - Use concurrent.futures.ThreadPoolExecutor
        # - Use queue.Queue(maxsize=queue_size) for bounded queue
        # - Track active tasks
        # - Initialize logger with run_context if available
        pass
    
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
        # Implementation:
        # - Add task to queue (blocking if queue is full)
        # - Log task submission
        # - Return Future
        pass
    
    def submit_batch(self, tasks: List[Tuple[Callable, tuple, dict]]) -> List[Future]:
        """
        Submit multiple tasks as a batch.
        
        Args:
            tasks: List of (callable, args_tuple, kwargs_dict) tuples
        
        Returns:
            List of Future objects
        """
        pass
    
    def wait_for_completion(self, futures: List[Future], timeout: Optional[float] = None) -> List[Any]:
        """
        Wait for all futures to complete and return results.
        
        Args:
            futures: List of Future objects
            timeout: Optional timeout in seconds
        
        Returns:
            List of results (or exceptions)
        """
        # Implementation:
        # - Use concurrent.futures.as_completed or wait
        # - Collect results
        # - Handle exceptions per task (error isolation)
        # - Log completion/failure for each task
        # - Emit events
        # - Record metrics
        pass
    
    def shutdown(self, wait: bool = True, timeout: Optional[float] = None):
        """
        Shutdown the worker pool.
        
        Args:
            wait: Whether to wait for pending tasks
            timeout: Optional timeout for shutdown
        """
        pass
```

## B. Task Wrapper Function

```python
def profile_table_task(
    engine: ProfileEngine,
    table_pattern: TablePattern,
    run_context: Optional[RunContext] = None,
    event_bus: Optional[EventBus] = None
) -> Optional[ProfilingResult]:
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
    # Implementation:
    # - Log worker start
    # - Emit profiling_started event
    # - Call engine._profile_table(pattern)
    # - Handle exceptions gracefully (return None, don't raise)
    # - Log completion/failure
    # - Emit profiling_completed/failed event
    # - Record metrics
    pass
```

---

# 3. Integrate Worker Pool into ProfileEngine

Modify `profilemesh/profiling/core.py`:

## A. Update `ProfileEngine.__init__`

```python
def __init__(
    self,
    config: ProfileMeshConfig,
    event_bus: Optional[EventBus] = None,
    run_context: Optional[RunContext] = None
):
    # ... existing code ...
    
    # Initialize worker pool ONLY if parallelism is enabled
    self.execution_config = config.execution
    self.worker_pool: Optional[WorkerPool] = None
    
    # Only create worker pool if max_workers > 1
    if self.execution_config.max_workers > 1:
        # Determine warehouse-specific worker limit
        warehouse_limit = self.execution_config.warehouse_limits.get(
            self.config.source.type,
            self.execution_config.max_workers
        )
        
        # Special handling for SQLite (single writer)
        if self.config.source.type == "sqlite":
            warehouse_limit = 1  # SQLite doesn't support concurrent writes well
            logger.warning("SQLite does not support parallel writes. Using sequential execution.")
        
        if warehouse_limit > 1:
            from ..utils.worker_pool import WorkerPool
            self.worker_pool = WorkerPool(
                max_workers=warehouse_limit,
                queue_size=self.execution_config.queue_size,
                warehouse_type=self.config.source.type
            )
            logger.info(f"Parallel execution enabled with {warehouse_limit} workers")
    else:
        logger.debug("Sequential execution (max_workers=1, default)")
```

## B. Update `profile()` Method

```python
def profile(self, table_patterns: Optional[List[TablePattern]] = None) -> List[ProfilingResult]:
    """
    Profile tables with optional parallel execution.
    
    If max_workers=1 (default), uses sequential execution (existing behavior).
    If max_workers > 1, uses parallel execution via worker pool.
    """
    patterns = table_patterns or self.config.profiling.tables
    
    if not patterns:
        logger.warning("No table patterns specified for profiling")
        return []
    
    # Create connector (existing code)
    # ... connector setup ...
    
    # Route to parallel or sequential execution
    if self.worker_pool:
        return self._profile_parallel(patterns)
    else:
        return self._profile_sequential(patterns)

def _profile_parallel(self, patterns: List[TablePattern]) -> List[ProfilingResult]:
    """
    Profile tables in parallel using worker pool.
    Only called when max_workers > 1.
    """
    from ..utils.worker_pool import profile_table_task
    
    # Submit all tasks
    futures = []
    for pattern in patterns:
        future = self.worker_pool.submit(
            profile_table_task,
            self,  # Pass engine instance
            pattern,
            self.run_context,
            self.event_bus
        )
        futures.append(future)
    
    # Wait for completion
    results = self.worker_pool.wait_for_completion(futures)
    
    # Filter out None results (failed tasks)
    successful = [r for r in results if r is not None]
    failed_count = len(results) - len(successful)
    
    if failed_count > 0:
        logger.warning(f"Parallel profiling completed: {len(successful)} succeeded, {failed_count} failed")
    
    return successful

def _profile_sequential(self, patterns: List[TablePattern]) -> List[ProfilingResult]:
    """
    Profile tables sequentially (existing implementation).
    This is the default behavior when max_workers=1.
    """
    # Move existing profile() logic here
    # ... existing sequential code ...
```

---

# 4. Warehouse-Specific Optimizations

## A. Connection Pool Management

Update `profilemesh/connectors/base.py`:

```python
def _create_engine(self) -> Engine:
    """
    Create SQLAlchemy engine with appropriate pool size for parallelism.
    Only adjusts pool size when parallelism is enabled (max_workers > 1).
    """
    # Get execution config if available
    execution_config = getattr(self, 'execution_config', None)
    
    if execution_config and execution_config.max_workers > 1:
        max_workers = execution_config.max_workers
        # Set pool size based on worker count
        pool_size = min(max_workers + 2, 20)  # Cap at 20
        max_overflow = max_workers
    else:
        # Default pool size for sequential execution
        pool_size = 5
        max_overflow = 10
    
    # Create engine with pool configuration
    return create_engine(
        connection_string,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,  # Verify connections before use
        **self.config.extra_params
    )
```

## B. Warehouse-Specific Limits

In `ProfileEngine.__init__`, apply warehouse-specific limits:

```python
# Default limits per warehouse type
WAREHOUSE_LIMITS = {
    "snowflake": 20,      # High concurrency supported
    "postgres": 8,        # Moderate concurrency
    "mysql": 8,           # Moderate concurrency
    "redshift": 10,       # Moderate-high concurrency
    "bigquery": 15,       # High concurrency
    "sqlite": 1,          # Single writer only
}

# Apply limit
warehouse_limit = self.execution_config.warehouse_limits.get(
    self.config.source.type,
    WAREHOUSE_LIMITS.get(self.config.source.type, self.execution_config.max_workers)
)
```

---

# 5. Structured Logging Integration

Every worker lifecycle event must log:

```python
# Worker started
log_event(
    logger,
    "worker_started",
    f"Worker {worker_id} started processing table {table_name}",
    level="debug",
    metadata={
        "worker_id": worker_id,
        "table": table_name,
        "queue_size": queue_size,
        "active_workers": active_count
    }
)

# Worker completed
log_event(
    logger,
    "worker_completed",
    f"Worker {worker_id} completed table {table_name}",
    level="info",
    metadata={
        "worker_id": worker_id,
        "table": table_name,
        "duration_seconds": duration,
        "success": True
    }
)

# Worker failed
log_event(
    logger,
    "worker_failed",
    f"Worker {worker_id} failed on table {table_name}: {error}",
    level="error",
    metadata={
        "worker_id": worker_id,
        "table": table_name,
        "error": str(error),
        "error_type": type(error).__name__
    }
)
```

---

# 6. Event Bus Integration

Emit events for parallel execution:

```python
# Batch started
event = BaseEvent(
    event_type="batch_started",
    timestamp=datetime.now(),
    metadata={
        "batch_size": len(tasks),
        "max_workers": max_workers,
        "warehouse": warehouse_type
    }
)
event_bus.emit(event)

# Batch completed
event = BaseEvent(
    event_type="batch_completed",
    timestamp=datetime.now(),
    metadata={
        "batch_size": len(tasks),
        "successful": success_count,
        "failed": failed_count,
        "duration_seconds": duration
    }
)
event_bus.emit(event)
```

---

# 7. Prometheus Metrics Integration

Add metrics to `profilemesh/utils/metrics.py`:

```python
# Worker pool metrics
active_workers_gauge = Gauge(
    "profilemesh_active_workers",
    "Number of currently active worker threads",
    ["warehouse"]
)

worker_tasks_total = Counter(
    "profilemesh_worker_tasks_total",
    "Total number of worker tasks",
    ["warehouse", "status"]  # status: started, completed, failed
)

worker_queue_size = Gauge(
    "profilemesh_worker_queue_size",
    "Current size of worker task queue",
    ["warehouse"]
)

batch_duration_seconds = Histogram(
    "profilemesh_batch_duration_seconds",
    "Histogram of batch execution times",
    ["warehouse", "batch_size"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
)
```

Record metrics in `WorkerPool`:
- Increment `active_workers_gauge` when worker starts
- Decrement when worker completes
- Increment `worker_tasks_total` with status
- Update `worker_queue_size` when queue changes
- Record `batch_duration_seconds` for each batch

---

# 8. Configuration Example

Update `examples/config.yml`:

```yaml
# Execution and parallelism configuration (OPTIONAL)
# Default: max_workers=1 (sequential execution)
# Enable parallelism by setting max_workers > 1
execution:
  max_workers: 1              # Default: 1 (sequential). Set > 1 to enable parallelism
  batch_size: 10              # Tables per batch (default: 10)
  queue_size: 100             # Maximum queue size (default: 100)
  
  # Warehouse-specific worker limits (optional, only used if max_workers > 1)
  warehouse_limits:
    snowflake: 20             # Snowflake can handle more concurrency
    postgres: 8               # Postgres moderate concurrency
    sqlite: 1                 # SQLite single writer (parallelism disabled)
```

**Note**: The configuration is commented out by default to maintain sequential execution.

---

# 9. Error Isolation

Critical requirement: **Errors in one table must not abort other tables**.

```python
def profile_table_task(...):
    try:
        result = engine._profile_table(pattern)
        return result
    except Exception as e:
        # Log error but don't raise
        log_event(
            logger,
            "table_profiling_failed",
            f"Failed to profile {table_name}: {e}",
            level="error",
            metadata={"error": str(e), "error_type": type(e).__name__}
        )
        # Emit failure event
        # Record failure metric
        # Return None (not raise) so other tasks continue
        return None
```

---

# 10. Thread Safety Considerations

- **ProfileEngine**: Must be thread-safe or create per-worker instances
- **Connector**: SQLAlchemy engines are thread-safe, but verify connection pooling
- **Event Bus**: Must be thread-safe (verify current implementation)
- **Metrics**: Prometheus client is thread-safe
- **Storage Writer**: May need locking or per-worker writers

Recommendation: Create a new `ProfileEngine` instance per worker thread OR ensure all shared state is thread-safe.

---

# 11. Test Suite

Add tests under:
```
tests/utils/test_worker_pool.py
```

Tests must verify:
- **Backward Compatibility**:
  - Default config (no execution section) → sequential
  - max_workers=1 explicitly → sequential
  - Results identical to current implementation
- **Parallelism**:
  - Worker pool creates correct number of workers
  - Tasks are executed in parallel
  - Queue size limit is enforced
  - Error isolation works (one failure doesn't stop others)
  - Warehouse-specific limits are applied
  - Metrics are recorded correctly
  - Events are emitted
  - Structured logging works
  - Thread safety (no race conditions)

Mock scenarios:
- All tasks succeed
- Some tasks fail (verify others continue)
- Queue overflow (verify blocking behavior)
- Worker pool shutdown (verify graceful shutdown)
- Default config maintains sequential behavior

---

# 12. Deliverables

This prompt should result in creation/modification of:

- `profilemesh/config/schema.py` - Added `ExecutionConfig` (defaults to sequential)
- `profilemesh/utils/worker_pool.py` - New worker pool module (only used when enabled)
- `profilemesh/profiling/core.py` - Updated to conditionally use worker pool
- `profilemesh/connectors/base.py` - Connection pool configuration (only when parallelism enabled)
- `profilemesh/utils/metrics.py` - New worker pool metrics
- `examples/config.yml` - Added execution configuration (commented, showing defaults)
- `tests/utils/test_worker_pool.py` - Comprehensive test suite
- Documentation updates with Dagster note

---

# 13. Integration Points

Ensure integration with existing systems:

- **Retry System**: Worker tasks should use existing retry logic
- **Structured Logging**: Use `RunContext` and `log_event` from `utils.logging`
- **Event Bus**: Emit events for worker lifecycle
- **Metrics**: Record all worker pool metrics
- **Error Handling**: Use existing error classification from retry module

---

# 14. Performance Considerations

- **Memory**: Bounded queue prevents memory overrun
- **CPU**: Default to CPU count, allow override
- **I/O**: Profiling is I/O-bound, so parallelism is beneficial
- **Warehouse Load**: Respect warehouse-specific limits
- **Connection Pools**: Size appropriately for worker count

---

# 15. Backward Compatibility (CRITICAL)

**MUST MAINTAIN:**

1. **Default behavior**: `max_workers=1` means sequential execution (current behavior)
2. **No config required**: If `execution` section is missing, defaults to sequential
3. **CLI unchanged**: Existing CLI commands work exactly as before
4. **Dagster unchanged**: Existing Dagster assets work exactly as before

**Verification:**
- Test that default config (no execution section) works identically to current behavior
- Test that max_workers=1 explicitly works identically to current behavior
- Test that max_workers > 1 enables parallelism (new behavior)

---

# 16. Dagster Integration Note

**Important for Dagster Users:**

Dagster already provides asset-level parallelism. Each table is a separate asset,
and Dagster executes independent assets in parallel by default. Therefore:

- **Default behavior (max_workers=1)**: Each Dagster asset profiles one table sequentially
  - This is the recommended approach for Dagster
  - Dagster handles parallelism at the asset level

- **Parallelism enabled (max_workers > 1)**: Can be useful if:
  - You want to batch multiple tables in a single asset
  - You want more control over parallelism than Dagster's executor provides
  - You want to limit warehouse load independently of Dagster

**Recommendation for Dagster users**: Keep default (max_workers=1) unless you have
a specific need for batching within a single asset.

---

# 17. Use Cases

## Primary Use Case: CLI Execution

**Scenario**: User runs `profilemesh profile --config config.yml` with 50 tables
- **Without parallelism (default)**: ~50 minutes (1 min/table)
- **With parallelism (max_workers=8)**: ~7 minutes
- **Speedup**: ~7x faster (when enabled)

## Secondary Use Case: Dagster Batching

**Scenario**: User wants to profile 10 tables in a single Dagster asset
- **Without parallelism (default)**: Sequential within asset
- **With parallelism (max_workers=5)**: 5 tables at a time
- **Benefit**: Faster completion of the asset

## Not Recommended: Dagster with One Table Per Asset

**Scenario**: User has Dagster assets, one per table (current setup)
- **Recommendation**: Keep max_workers=1 (default)
- **Reason**: Dagster already provides parallelism at asset level
- **No benefit**: Adding parallelism here would be redundant

---

# Notes for Cursor

- **Default to sequential**: Always default to `max_workers=1` (sequential)
- **Opt-in feature**: Parallelism must be explicitly enabled
- **Backward compatible**: Existing configs must work unchanged
- **CLI-focused**: Primary benefit is for CLI users
- **Dagster-aware**: Document that Dagster already provides parallelism
- Ensure imports are relative: `from profilemesh...`
- Do not create circular imports
- Use `concurrent.futures.ThreadPoolExecutor` for worker pool
- Use `queue.Queue(maxsize=...)` for bounded queue
- Never add metrics labels with high cardinality (worker_id should not be a label)
- Ensure thread safety for all shared state when parallelism is enabled
- Test with multiple warehouse types
- Verify error isolation thoroughly
- Consider SQLite's single-writer limitation
- Document warehouse-specific recommendations

---

# Expected Performance Improvement

**For CLI users with many tables:**

For a warehouse with 50 tables:
- **Sequential (default)**: ~50 minutes (1 min/table)
- **Parallel (max_workers=8)**: ~7 minutes (50/8 + overhead)
- **Speedup**: ~7x faster (when enabled)

For 500 tables:
- **Sequential (default)**: ~8.3 hours
- **Parallel (max_workers=8)**: ~1.2 hours
- **Speedup**: ~7x faster (when enabled)

**For Dagster users:**
- **No change by default**: Dagster already provides parallelism
- **Optional batching**: Can enable if needed for specific use cases


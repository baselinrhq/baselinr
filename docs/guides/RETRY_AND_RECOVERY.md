# Retry and Recovery System

Baselinr includes a robust retry and recovery system that automatically handles transient warehouse failures, protecting your profiling operations from temporary network issues, connection timeouts, and rate limits.

## Overview

The retry system:
- ✅ **Automatically retries** failed warehouse operations on transient errors
- ✅ **Exponential backoff** with jitter prevents overwhelming the warehouse
- ✅ **Intelligent error classification** distinguishes transient from permanent errors
- ✅ **Structured logging** tracks all retry attempts
- ✅ **Event emission** publishes retry events to the event bus
- ✅ **Prometheus metrics** monitor retry behavior
- ✅ **Graceful degradation** continues profiling remaining tables after failures

## Configuration

Add the `retry` section to your `config.yml`:

```yaml
retry:
  enabled: true                 # Enable retry logic (default: true)
  retries: 3                    # Maximum retry attempts (0-10, default: 3)
  backoff_strategy: exponential # Options: exponential | fixed (default: exponential)
  min_backoff: 0.5             # Minimum delay in seconds (default: 0.5)
  max_backoff: 8.0             # Maximum delay in seconds (default: 8.0)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | `true` | Enable/disable retry logic globally |
| `retries` | int | `3` | Maximum number of retry attempts (0-10) |
| `backoff_strategy` | str | `exponential` | Backoff strategy: `exponential` or `fixed` |
| `min_backoff` | float | `0.5` | Minimum backoff delay in seconds |
| `max_backoff` | float | `8.0` | Maximum backoff delay in seconds |

### Backoff Strategies

#### Exponential Backoff (Recommended)

Delays increase exponentially: 0.5s → 1s → 2s → 4s → 8s (capped at `max_backoff`)

```yaml
retry:
  backoff_strategy: exponential
  min_backoff: 0.5
  max_backoff: 8.0
```

**Benefits:**
- Gives the warehouse more time to recover
- Reduces load on struggling systems
- Includes jitter (±15%) to prevent thundering herd

#### Fixed Backoff

All delays use the same duration (`min_backoff`)

```yaml
retry:
  backoff_strategy: fixed
  min_backoff: 2.0
```

**Use cases:**
- Rate-limited APIs with fixed reset intervals
- Testing and development

## Error Classification

Baselinr automatically classifies database errors as **transient** (retryable) or **permanent** (not retryable).

### Transient Errors (Retried)

These errors are automatically retried:

| Error Type | Examples |
|------------|----------|
| **Timeouts** | Query timeout, connection timeout |
| **Connection Issues** | Connection reset, connection lost, broken pipe |
| **Rate Limits** | Too many requests, rate limit exceeded |
| **Deadlocks** | Deadlock detected, lock timeout |
| **Network Errors** | Network error, I/O error, communication failure |
| **Temporary Issues** | Temporarily unavailable, connection pool exhausted |

### Permanent Errors (Not Retried)

These errors fail immediately without retry:
- **Syntax errors** - Invalid SQL
- **Authentication failures** - Wrong credentials
- **Permission denied** - Insufficient privileges
- **Table/schema not found** - Missing objects
- **Data type errors** - Type mismatch
- **Constraint violations** - Unique constraint, foreign key violations

## How It Works

### 1. Warehouse Operations

All warehouse operations are automatically wrapped with retry logic:

```python
# These operations are automatically protected:
connector.execute_query(sql)         # SQL queries
connector.list_schemas()              # Schema introspection
connector.list_tables(schema)         # Table listing
connector.get_table(name, schema)     # Table metadata
```

### 2. Retry Flow

```
┌─────────────────────────────────────────────────────┐
│ 1. Execute warehouse operation                      │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 2. Success? ──YES──> Return result                  │
│         │                                            │
│        NO                                            │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│ 3. Classify error                                    │
│    • Transient? ──NO──> Raise immediately           │
│    • Permanent? ──YES─> Raise immediately           │
└────────┬────────────────────────────────────────────┘
         │
         ▼ (Transient error)
┌─────────────────────────────────────────────────────┐
│ 4. Check retry budget                                │
│    • Retries exhausted? ──YES──> Raise error        │
│    • Budget available? ──NO──> Continue             │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│ 5. Wait with backoff                                 │
│    • Calculate delay (exponential/fixed + jitter)    │
│    • Log retry attempt                               │
│    • Emit retry event                                │
│    • Increment metrics                               │
└────────┬────────────────────────────────────────────┘
         │
         └──────> Back to step 1 (retry operation)
```

### 3. Exponential Backoff with Jitter

```python
# Calculate base delay
delay = min(max_backoff, min_backoff * (2 ** attempt))

# Add jitter (0-15% of delay)
delay += random.uniform(0, delay * 0.15)

# Example with defaults:
# Attempt 1: 0.5s + jitter = 0.5-0.58s
# Attempt 2: 1.0s + jitter = 1.0-1.15s
# Attempt 3: 2.0s + jitter = 2.0-2.30s
# Attempt 4: 4.0s + jitter = 4.0-4.60s
# Attempt 5: 8.0s + jitter = 8.0-9.20s (capped)
```

## Observability

### Structured Logging

Every retry attempt is logged with full context:

```json
{
  "event": "retry_attempt",
  "level": "warning",
  "run_id": "abc-123",
  "function": "execute_query",
  "attempt": 2,
  "error": "Connection timeout",
  "error_type": "TimeoutError",
  "backoff_seconds": 1.12
}
```

When retries are exhausted:

```json
{
  "event": "retry_exhausted",
  "level": "error",
  "run_id": "abc-123",
  "function": "execute_query",
  "total_attempts": 4,
  "error": "Connection timeout",
  "error_type": "TimeoutError"
}
```

### Event Bus Integration

Retry events are published to the event bus for custom handling:

**Event: `retry_attempt`**
```python
{
  "event_type": "retry_attempt",
  "timestamp": "2025-11-15T20:45:00Z",
  "metadata": {
    "function": "execute_query",
    "attempt": 2,
    "error": "Connection timeout",
    "error_type": "TimeoutError"
  }
}
```

**Event: `retry_exhausted`**
```python
{
  "event_type": "retry_exhausted",
  "timestamp": "2025-11-15T20:45:15Z",
  "metadata": {
    "function": "execute_query",
    "total_attempts": 4,
    "error": "Connection timeout",
    "error_type": "TimeoutError"
  }
}
```

### Prometheus Metrics

Monitor retry behavior with Prometheus metrics:

**Metric: `baselinr_warehouse_transient_errors_total`**
- Type: Counter
- Description: Total number of transient warehouse errors encountered
- Use: Track frequency of retryable errors

**Metric: `baselinr_errors_total{error_type="TimeoutError"}`**
- Type: Counter
- Description: Total errors by type
- Use: Identify most common error types

**Query Examples:**

```promql
# Rate of transient errors
rate(baselinr_warehouse_transient_errors_total[5m])

# Most common error types
topk(5, sum by (error_type) (baselinr_errors_total))

# Success rate after retries
(baselinr_profile_runs_total{status="completed"} /
 baselinr_profile_runs_total) * 100
```

## Best Practices

### 1. **Use Exponential Backoff for Production**

```yaml
retry:
  backoff_strategy: exponential  # Better for production
  min_backoff: 0.5
  max_backoff: 8.0
```

### 2. **Adjust Retry Count Based on Warehouse**

```yaml
# Flaky network/cloud warehouse
retry:
  retries: 5

# Stable on-premise warehouse
retry:
  retries: 2

# Testing/development
retry:
  retries: 1
```

### 3. **Set Appropriate Backoff Limits**

```yaml
# Fast-paced profiling (short tables)
retry:
  min_backoff: 0.5
  max_backoff: 4.0

# Long-running profiling (large tables)
retry:
  min_backoff: 1.0
  max_backoff: 30.0
```

### 4. **Monitor Retry Metrics**

Create Grafana alerts for excessive retries:

```promql
# Alert if retry rate exceeds 10/minute
rate(baselinr_warehouse_transient_errors_total[1m]) > 10
```

### 5. **Handle Retry Events**

Create a custom hook to alert on retry exhaustion:

```python
from baselinr.events import BaseEvent, Hook

class RetryAlertHook(Hook):
    def can_handle(self, event: BaseEvent) -> bool:
        return event.event_type == "retry_exhausted"
    
    def handle_event(self, event: BaseEvent) -> None:
        # Send alert to monitoring system
        send_alert(
            severity="high",
            message=f"Retry exhausted: {event.metadata['function']}"
        )
```

## Programmatic Usage

### Using the Decorator

```python
from baselinr.utils.retry import retry_with_backoff, TimeoutError

@retry_with_backoff(
    retries=3,
    backoff_strategy="exponential",
    min_backoff=0.5,
    max_backoff=8.0,
    retry_on=(TimeoutError, ConnectionLostError)
)
def query_warehouse(sql: str):
    return warehouse.execute(sql)

# This function will automatically retry on TimeoutError or ConnectionLostError
result = query_warehouse("SELECT * FROM table")
```

### Using the Wrapper Function

```python
from baselinr.utils.retry import retryable_call, TimeoutError

def query_warehouse(sql: str):
    return warehouse.execute(sql)

# Wrap the call with retry logic
result = retryable_call(
    query_warehouse,
    "SELECT * FROM table",
    retries=3,
    min_backoff=0.5,
    retry_on=(TimeoutError,)
)
```

### Custom Error Classification

```python
from baselinr.utils.retry import classify_database_error

try:
    warehouse.execute(sql)
except Exception as e:
    classified = classify_database_error(e)
    # classified is now TransientWarehouseError or PermanentWarehouseError
    raise classified
```

## Troubleshooting

### Problem: Too many retries

**Symptoms:**
- Profiling takes very long
- Many retry attempts in logs

**Solutions:**
1. Reduce `retries` count
2. Decrease `max_backoff`
3. Check warehouse health

### Problem: Retries not working

**Symptoms:**
- Errors fail immediately
- No retry attempts logged

**Check:**
1. Ensure `retry.enabled: true`
2. Verify error is classified as transient
3. Check retry budget (`retries > 0`)

### Problem: Excessive backoff delays

**Symptoms:**
- Long delays between attempts
- Timeout before retries complete

**Solutions:**
1. Reduce `max_backoff`
2. Switch to `fixed` backoff strategy
3. Decrease `min_backoff`

## Performance Impact

### Overhead

- **Success case:** ~0.1ms overhead (negligible)
- **Retry case:** Adds backoff delay (0.5s - 8.0s per retry)
- **Memory:** Minimal (&lt;1KB per operation)

### Recommended Settings

| Workload | Retries | Min Backoff | Max Backoff | Strategy |
|----------|---------|-------------|-------------|----------|
| Development | 1 | 0.1s | 1.0s | fixed |
| Testing | 2 | 0.5s | 4.0s | exponential |
| Production (stable) | 3 | 0.5s | 8.0s | exponential |
| Production (flaky) | 5 | 1.0s | 16.0s | exponential |

## Related Documentation

- [Configuration Guide](../getting-started/INSTALL.md)
- [Event System](../architecture/EVENTS_AND_HOOKS.md)
- [Prometheus Metrics](PROMETHEUS_METRICS.md)
- [Error Handling](../development/DEVELOPMENT.md)

## Support

For issues or questions about retry behavior:
1. Check structured logs for retry events
2. Monitor Prometheus metrics for patterns
3. Verify error classification is correct
4. Report issues on GitHub with logs and config


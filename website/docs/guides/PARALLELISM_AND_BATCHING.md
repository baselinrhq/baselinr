# Parallelism and Batching Guide

This guide explains how to use Baselinr's optional parallelism and batching features to speed up profiling operations.

## Table of Contents

- [Overview](#overview)
- [When to Use Parallelism](#when-to-use-parallelism)
- [Configuration](#configuration)
- [How It Works](#how-it-works)
- [Warehouse-Specific Considerations](#warehouse-specific-considerations)
- [Dagster Integration](#dagster-integration)
- [Performance Impact](#performance-impact)
- [Troubleshooting](#troubleshooting)

---

## Overview

Baselinr supports **optional** parallel execution of profiling tasks. This feature is:

- **Opt-in**: Defaults to sequential execution (max_workers=1)
- **CLI-focused**: Primary benefit is for CLI users profiling many tables
- **Dagster-compatible**: Works with Dagster but not required (Dagster already provides asset-level parallelism)
- **Backward compatible**: Existing configurations work unchanged

**Key Design Decision:**
- **Default**: `max_workers=1` (sequential execution, maintains current behavior)
- **Opt-in**: Users enable parallelism via configuration
- **Primary use case**: CLI execution where users want to profile many tables faster

---

## When to Use Parallelism

### ✅ Use Parallelism When:

1. **CLI execution** with many tables (10+ tables)
2. Profiling large warehouses (hundreds of tables)
3. Tables are independent (no cross-table dependencies)
4. Warehouse can handle concurrent connections
5. Want to reduce total profiling time

**Example**: Profiling 50 tables sequentially takes ~50 minutes. With 8 workers, it takes ~7 minutes.

### ❌ Don't Use Parallelism When:

1. **Dagster users** with one table per asset (Dagster already parallelizes at the asset level)
2. Using SQLite (single writer limitation)
3. Warehouse has connection limits
4. Profiling only 1-2 tables (no benefit)
5. Debugging profiling issues (sequential is easier to debug)

---

## Configuration

### Basic Configuration

Add the `execution` section to your `config.yml`:

```yaml
# Execution and parallelism configuration (OPTIONAL)
# Default: max_workers=1 (sequential execution)
# Enable parallelism by setting max_workers > 1
execution:
  max_workers: 8          # Number of concurrent workers
  batch_size: 10          # Tables per batch (default: 10)
  queue_size: 100         # Maximum queue size (default: 100)
```

### Warehouse-Specific Limits

You can set different worker limits for different warehouse types:

```yaml
execution:
  max_workers: 16         # Default for all warehouses
  
  # Warehouse-specific overrides
  warehouse_limits:
    snowflake: 20         # Snowflake can handle high concurrency
    postgres: 8           # Postgres moderate concurrency
    mysql: 8              # MySQL moderate concurrency
    redshift: 10          # Redshift moderate-high concurrency
    bigquery: 15          # BigQuery high concurrency
    sqlite: 1             # SQLite single writer only
```

### Configuration Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `max_workers` | 1 | 1-64 | Number of concurrent worker threads |
| `batch_size` | 10 | 1-100 | Tables per batch (for future use) |
| `queue_size` | 100 | 10-1000 | Maximum task queue size |
| `warehouse_limits` | {} | - | Per-warehouse worker limits |

---

## How It Works

### Sequential Execution (Default)

When `max_workers=1` (default), Baselinr profiles tables one at a time:

```
Table 1 → Table 2 → Table 3 → ... → Table N
```

**Characteristics:**
- Simple, predictable
- Easy to debug
- No connection pool pressure
- Existing behavior (backward compatible)

### Parallel Execution

When `max_workers > 1`, Baselinr uses a thread pool to profile multiple tables concurrently:

```
Worker 1: Table 1 → Table 5 → Table 9
Worker 2: Table 2 → Table 6 → Table 10
Worker 3: Table 3 → Table 7 → Table 11
Worker 4: Table 4 → Table 8 → Table 12
```

**Characteristics:**
- Faster total time
- Higher database load
- Requires larger connection pool
- Error isolation (one table failure doesn't stop others)

### Connection Pool Sizing

Baselinr automatically adjusts the database connection pool based on `max_workers`:

- **Sequential** (max_workers=1): pool_size=5, max_overflow=10
- **Parallel** (max_workers=8): pool_size=10 (8+2), max_overflow=8
- **Capped at 20**: pool_size never exceeds 20

---

## Warehouse-Specific Considerations

### Snowflake

- **Recommended max_workers**: 10-20
- **Notes**: Handles high concurrency well, scales horizontally
- **Connection limit**: Check your warehouse size and tier

```yaml
execution:
  max_workers: 20
  warehouse_limits:
    snowflake: 20
```

### Postgres

- **Recommended max_workers**: 4-8
- **Notes**: Limited by `max_connections` setting (default 100)
- **Connection limit**: `SHOW max_connections;`

```yaml
execution:
  max_workers: 8
  warehouse_limits:
    postgres: 8
```

### MySQL

- **Recommended max_workers**: 4-8
- **Notes**: Similar to Postgres, check `max_connections`
- **Connection limit**: `SHOW VARIABLES LIKE 'max_connections';`

```yaml
execution:
  max_workers: 8
  warehouse_limits:
    mysql: 8
```

### BigQuery

- **Recommended max_workers**: 10-15
- **Notes**: Cloud-based, scales automatically
- **Rate limits**: Be aware of project-level query quotas

```yaml
execution:
  max_workers: 15
  warehouse_limits:
    bigquery: 15
```

### Redshift

- **Recommended max_workers**: 8-12
- **Notes**: WLM (Workload Management) affects concurrency
- **Connection limit**: Check `max_connections` parameter

```yaml
execution:
  max_workers: 10
  warehouse_limits:
    redshift: 10
```

### SQLite

- **Recommended max_workers**: 1 (forced)
- **Notes**: Single writer limitation
- **Behavior**: Baselinr automatically forces sequential execution for SQLite

```yaml
execution:
  max_workers: 1  # SQLite ignores values > 1
```

---

## Dagster Integration

### Important for Dagster Users

**Dagster already provides asset-level parallelism.** Each table is a separate asset, and Dagster executes independent assets in parallel by default.

#### Default Behavior (Recommended for Dagster)

Keep `max_workers=1` (default). Dagster handles parallelism:

```yaml
# Recommended for Dagster users
execution:
  max_workers: 1  # Sequential within each asset
```

**Dagster will still parallelize** across assets:

```
Dagster Asset 1 (customers)  ─┐
Dagster Asset 2 (products)   ─┤─── Parallel at asset level
Dagster Asset 3 (orders)     ─┘
```

#### When Parallelism Helps in Dagster

Parallelism can be useful if:

1. **Batching multiple tables in a single asset**
   ```python
   @asset
   def profile_all_dimension_tables():
       # Profile 10 dimension tables in parallel within this asset
       config = load_config()  # max_workers=5
       engine = ProfileEngine(config)
       engine.profile()  # Profiles 5 tables at a time
   ```

2. **Fine-grained control over warehouse load**
   ```yaml
   execution:
     max_workers: 4
     warehouse_limits:
       postgres: 4  # Limit load independently of Dagster executor
   ```

3. **Want more control than Dagster's executor provides**

---

## Performance Impact

### Expected Speedup

For CLI users with many tables:

| Tables | Sequential | Parallel (8 workers) | Speedup |
|--------|------------|---------------------|---------|
| 10     | ~10 min    | ~2 min              | ~5x     |
| 50     | ~50 min    | ~7 min              | ~7x     |
| 100    | ~100 min   | ~15 min             | ~7x     |
| 500    | ~8.3 hrs   | ~1.2 hrs            | ~7x     |

*Assumes 1 minute per table on average*

### Factors Affecting Performance

1. **I/O bound**: Profiling is mostly I/O (database queries), so parallelism helps significantly
2. **Warehouse capacity**: More concurrent queries = more warehouse load
3. **Network latency**: Higher latency benefits more from parallelism
4. **Table size**: Large tables may still bottleneck
5. **Query complexity**: Simple metrics profile faster than complex ones

---

## Troubleshooting

### Issue: No performance improvement

**Symptoms**: Parallel execution is no faster than sequential

**Possible causes**:
1. Warehouse is the bottleneck (saturated)
2. Too few tables to benefit from parallelism
3. Connection pool is limiting
4. Network bandwidth is limiting

**Solutions**:
- Check warehouse CPU/memory usage
- Increase warehouse size (Snowflake) or connections (Postgres)
- Verify `max_workers` is > 1
- Check connection pool settings

### Issue: Connection errors

**Symptoms**: `Too many connections` or `Connection refused`

**Possible causes**:
1. `max_workers` exceeds warehouse connection limit
2. Other applications are using connections
3. Connection pool not properly sized

**Solutions**:
```yaml
execution:
  max_workers: 4  # Reduce workers
  warehouse_limits:
    postgres: 4   # Set warehouse-specific limit
```

Check warehouse connection limit:
```sql
-- Postgres
SHOW max_connections;
SELECT count(*) FROM pg_stat_activity;

-- MySQL
SHOW VARIABLES LIKE 'max_connections';
SHOW STATUS LIKE 'Threads_connected';
```

### Issue: SQLite errors with parallelism

**Symptoms**: Database locked errors

**Solution**: SQLite automatically forces sequential execution. This is expected behavior.

```yaml
execution:
  max_workers: 8  # Ignored for SQLite
  warehouse_limits:
    sqlite: 1     # Forced to 1
```

### Issue: One table fails, others succeed

**Symptoms**: Some tables profiled, one failed

**This is expected behavior** - error isolation ensures one table failure doesn't abort other tables.

Check logs for the specific failure:
```
ERROR: Failed to profile table orders: Connection timeout
INFO: Parallel profiling completed: 49 succeeded, 1 failed
```

### Issue: Metrics show no active workers

**Symptoms**: `baselinr_active_workers` metric is 0

**Possible causes**:
1. Metrics not enabled
2. Using sequential execution (max_workers=1)
3. No profiling currently running

**Check**:
```yaml
monitoring:
  enable_metrics: true

execution:
  max_workers: 8  # Must be > 1
```

---

## Best Practices

1. **Start small**: Try `max_workers=2` first, then scale up
2. **Monitor warehouse**: Watch CPU, memory, connections during parallel runs
3. **Use warehouse limits**: Set conservative per-warehouse limits
4. **CLI-focused**: Use parallelism primarily for CLI execution
5. **Dagster users**: Keep default (max_workers=1) unless batching
6. **Test thoroughly**: Verify results match sequential execution
7. **Watch logs**: Check for connection errors or timeouts
8. **Consider cost**: More parallelism = more warehouse compute cost

---

## Examples

### Example 1: CLI with many tables

```yaml
# Profile 100 tables in parallel
execution:
  max_workers: 8
  warehouse_limits:
    postgres: 8

profiling:
  tables:
    - table: table_001
    - table: table_002
    # ... 98 more tables
```

**Run**:
```bash
baselinr profile --config config.yml
```

**Expected**: ~7x faster than sequential

### Example 2: Dagster with batching

```python
# examples/dagster_repository.py
from baselinr.profiling.core import ProfileEngine
from baselinr.config.loader import load_config

@asset
def profile_dimension_tables():
    """Profile all dimension tables in parallel within this asset."""
    config = load_config("config_parallel.yml")
    engine = ProfileEngine(config)
    results = engine.profile()
    return results
```

```yaml
# config_parallel.yml
execution:
  max_workers: 5  # Profile 5 dimension tables concurrently

profiling:
  tables:
    - table: dim_customer
    - table: dim_product
    - table: dim_date
    - table: dim_location
    - table: dim_category
```

### Example 3: Warehouse-specific tuning

```yaml
# config_multiwarehouse.yml
execution:
  max_workers: 16  # Default

  # Fine-tuned per warehouse
  warehouse_limits:
    snowflake: 20   # Snowflake can handle more
    postgres: 8     # Postgres more conservative
    redshift: 12    # Redshift moderate
    sqlite: 1       # SQLite single writer
```

---

## Related Documentation

- [Configuration Schema](../architecture/CONFIG_SCHEMA.md)
- [Metrics and Monitoring](PROMETHEUS_METRICS.md)
- [Retry and Recovery](RETRY_AND_RECOVERY.md)
- [Dagster Integration](../development/DAGSTER_INTEGRATION.md)

---

## Support

If you encounter issues or have questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review logs for specific errors
3. Try sequential execution (max_workers=1) to isolate the issue
4. Reduce `max_workers` and scale up gradually


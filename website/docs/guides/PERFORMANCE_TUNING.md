# Performance Tuning Guide

Optimization guide for large-scale profiling and improved performance.

## Table of Contents

- [Overview](#overview)
- [Profiling Performance](#profiling-performance)
- [Sampling Strategies](#sampling-strategies)
- [Partition Strategies](#partition-strategies)
- [Parallelism Configuration](#parallelism-configuration)
- [Incremental Profiling](#incremental-profiling)
- [Database Optimization](#database-optimization)
- [Memory Optimization](#memory-optimization)
- [Network Optimization](#network-optimization)
- [Monitoring and Metrics](#monitoring-and-metrics)

## Overview

This guide covers optimization strategies for improving Baselinr performance at scale. Key areas include:

- Profiling speed: Reduce time to profile large tables
- Resource usage: Minimize CPU, memory, and network usage
- Cost optimization: Reduce database compute costs
- Scalability: Handle large numbers of tables efficiently

## Profiling Performance

### Reduce Metrics Computed

Limit the number of metrics computed to improve performance.

**Strategy:**

1. Remove expensive metrics for large tables:
   ```yaml
   profiling:
     tables:
       - table: large_table
         # Only essential metrics
         metrics:
           - count
           - null_ratio
           - distinct_count
           # Skip: histogram, mean, stddev for large tables
   ```

2. Use different metric sets per table:
   ```yaml
   profiling:
     tables:
       - table: critical_table
         # Full metrics
         metrics:
           - count
           - null_ratio
           - distinct_count
           - mean
           - stddev
           - histogram
       - table: large_table
         # Minimal metrics
         metrics:
           - count
           - null_ratio
           - distinct_count
   ```

**Performance Impact:**
- Removing `histogram`: 20-30% faster
- Removing `mean`/`stddev`: 10-15% faster
- Keeping only essential metrics: 40-50% faster

### Limit Distinct Values

Reduce `max_distinct_values` for high-cardinality columns.

**Strategy:**
```yaml
profiling:
  max_distinct_values: 100  # Default is 1000
```

**When to Use:**
- Tables with many high-cardinality columns
- When exact distinct counts aren't critical
- When you only need approximate counts

**Performance Impact:**
- Reduces query time for high-cardinality columns by 30-50%

### Disable Histograms When Not Needed

Histograms are expensive to compute but provide valuable distribution information.

**Strategy:**
```yaml
profiling:
  compute_histograms: false  # Disable for all tables
```

Or per-table:
```yaml
profiling:
  tables:
    - table: large_table
      # Override to disable histograms
      metadata:
        compute_histograms: false
```

**When to Disable:**
- Very large tables (&gt;100M rows)
- When distribution information isn't needed
- During initial profiling to establish baselines

**Performance Impact:**
- 20-40% faster profiling for tables with many numeric columns

## Sampling Strategies

### Random Sampling

Use random sampling for general-purpose profiling.

**Configuration:**
```yaml
profiling:
  tables:
    - table: very_large_table
      sampling:
        enabled: true
        method: random
        fraction: 0.01  # 1% sample
        max_rows: 1000000  # Cap at 1M rows
```

**Best Practices:**
- Use 1-5% fraction for very large tables
- Set `max_rows` to prevent excessive sampling time
- Higher fraction (5-10%) for smaller large tables

**Performance Impact:**
- 1% sample: 100x faster for row count and basic metrics
- Trade-off: Slight accuracy loss, but statistically valid

### Stratified Sampling

Use stratified sampling for skewed distributions.

**Configuration:**
```yaml
profiling:
  tables:
    - table: skewed_table
      sampling:
        enabled: true
        method: stratified
        fraction: 0.05  # 5% sample
        max_rows: 2000000
```

**When to Use:**
- Tables with highly skewed distributions
- When you need to capture rare values
- Categorical columns with long tails

**Performance Impact:**
- Similar to random sampling but better coverage of rare values

### Sampling Guidelines

| Table Size | Recommended Fraction | Max Rows |
|------------|---------------------|----------|
| &lt; 1M rows | 1.0 (no sampling) | N/A |
| 1M - 10M rows | 0.10 (10%) | 1M |
| 10M - 100M rows | 0.05 (5%) | 2M |
| 100M - 1B rows | 0.01 (1%) | 5M |
| > 1B rows | 0.005 (0.5%) | 10M |

## Partition Strategies

### Latest Partition Only

Profile only the latest partition for time-series data.

**Configuration:**
```yaml
profiling:
  tables:
    - table: events
      partition:
        key: event_date
        strategy: latest
```

**Performance Impact:**
- Dramatically faster for partitioned tables
- Only profiles recent data (good for drift detection)

### Recent N Partitions

Profile a rolling window of partitions.

**Configuration:**
```yaml
profiling:
  tables:
    - table: events
      partition:
        key: event_date
        strategy: recent_n
        recent_n: 7  # Last 7 days
```

**Performance Impact:**
- Faster than profiling all partitions
- Maintains some historical context

**Best Practices:**
- Use `recent_n` based on partition frequency:
  - Daily partitions: `recent_n: 7` (last week)
  - Hourly partitions: `recent_n: 24` (last day)
  - Monthly partitions: `recent_n: 3` (last quarter)

## Parallelism Configuration

### Enabling Parallelism

Enable parallel profiling for multiple tables.

**Configuration:**
```yaml
execution:
  max_workers: 4  # Process 4 tables in parallel
  batch_size: 10
  queue_size: 100
```

**Performance Impact:**
- Linear speedup up to database concurrency limit
- 4 workers: ~3.5x faster (accounting for overhead)

### Warehouse-Specific Limits

Set different worker limits per database type.

**Configuration:**
```yaml
execution:
  max_workers: 8  # Default limit
  warehouse_limits:
    snowflake: 20    # Snowflake can handle more
    postgres: 8      # Postgres moderate concurrency
    mysql: 6         # MySQL lower concurrency
    sqlite: 1        # SQLite single writer (no parallelism)
    bigquery: 10     # BigQuery query limits
    redshift: 8      # Redshift moderate concurrency
```

**Best Practices:**
- Start conservative and scale up
- Monitor database load and query queue
- Respect database connection limits
- Use read replicas if available

**Performance Impact:**
- Optimal worker count depends on database capacity
- Too many workers can cause contention and slowdown

### Finding Optimal Worker Count

Test different worker counts to find the optimal setting.

**Process:**
1. Start with `max_workers: 2`
2. Profile a representative set of tables
3. Measure total time
4. Increase workers and repeat
5. Stop when performance plateaus or degrades

**Example:**
```yaml
# Test configuration
execution:
  max_workers: 2  # Start here
  # ... profile and measure

# Then test
execution:
  max_workers: 4
  # ... profile and measure

# Continue until optimal
```

## Incremental Profiling

### Enable Incremental Profiling

Skip unchanged tables to improve performance.

**Configuration:**
```yaml
incremental:
  enabled: true
  change_detection:
    enabled: true
    metadata_table: baselinr_table_state
    snapshot_ttl_minutes: 1440  # 24 hours
```

**Performance Impact:**
- Skip 80-90% of tables that haven't changed
- 10-20x faster for typical production workloads

**Best Practices:**
- Enable for production deployments
- Set appropriate TTL based on update frequency
- Monitor false negatives (unchanged tables that should be profiled)

### Change Detection

Optimize change detection metadata cache.

**Configuration:**
```yaml
incremental:
  change_detection:
    enabled: true
    snapshot_ttl_minutes: 1440  # Cache for 24 hours
    connector_overrides:
      snowflake:
        # Snowflake-specific optimizations
        cache_partition_info: true
```

**Performance Impact:**
- Faster change detection with cached metadata
- Reduces database queries for metadata

### Partial Profiling

Enable partial profiling for partition-aware optimization.

**Configuration:**
```yaml
incremental:
  partial_profiling:
    enabled: true
    allow_partition_pruning: true
    max_partitions_per_run: 64
```

**Performance Impact:**
- Only profile changed partitions
- Significantly faster for partitioned tables

## Database Optimization

### Connection Pooling

Configure connection pooling appropriately.

**Best Practices:**
- Use appropriate pool size based on worker count
- Set reasonable connection timeouts
- Monitor connection pool usage

**Performance Impact:**
- Reduces connection overhead
- Better connection reuse

### Query Optimization

Optimize database queries where possible.

**Strategies:**
1. Use indexed columns for partition keys
2. Create indexes on frequently queried metadata tables
3. Use appropriate query timeouts

**Example (PostgreSQL):**
```sql
-- Index metadata tables for faster queries
CREATE INDEX idx_runs_profiled_at ON baselinr_runs(profiled_at DESC);
CREATE INDEX idx_results_run_id ON baselinr_results(run_id);
CREATE INDEX idx_results_dataset ON baselinr_results(dataset_name);
```

### Read Replicas

Use read replicas for profiling to reduce load on primary database.

**Configuration:**
```yaml
# Profile from read replica
source:
  type: postgres
  host: read-replica.example.com  # Use replica
  
# Store results in primary
storage:
  connection:
    type: postgres
    host: primary.example.com  # Use primary
```

**Performance Impact:**
- Reduces load on primary database
- Better performance isolation

## Memory Optimization

### Reduce Memory Footprint

Optimize memory usage for large tables.

**Strategies:**
1. Use sampling to reduce data scanned
2. Process tables sequentially instead of parallel (if memory-constrained)
3. Reduce metrics computed
4. Limit distinct values

**Configuration:**
```yaml
# Memory-optimized configuration
execution:
  max_workers: 1  # Sequential processing
profiling:
  max_distinct_values: 100  # Reduce memory usage
  compute_histograms: false  # Skip expensive metrics
```

### Streaming Results

Use streaming for very large result sets.

**Best Practices:**
- Results are streamed to storage automatically
- Don't load all results into memory at once
- Use query limits when querying results

## Network Optimization

### Reduce Network Latency

Optimize for network performance.

**Strategies:**
1. Co-locate Baselinr with database (same region/VPC)
2. Use connection pooling
3. Minimize round trips
4. Compress large payloads (if database supports)

**Performance Impact:**
- Lower latency improves overall performance
- Especially important for cloud databases

### Batch Operations

Use batch operations where possible.

**Best Practices:**
- Baselinr batches writes automatically
- Configure `batch_size` appropriately
- Monitor batch performance

## Monitoring and Metrics

### Enable Prometheus Metrics

Monitor performance metrics.

**Configuration:**
```yaml
monitoring:
  enable_metrics: true
  port: 9753
  keep_alive: true
```

**Key Metrics to Monitor:**
- Profiling duration per table
- Database query time
- Memory usage
- Parallel worker utilization
- Error rates

### Performance Baselines

Establish performance baselines.

**Process:**
1. Profile representative tables
2. Measure key metrics:
   - Total profiling time
   - Time per table
   - Database query time
   - Memory usage
3. Document baselines
4. Monitor for regressions

**Example:**
```
Baseline Performance (100 tables):
- Total time: 45 minutes
- Average time per table: 27 seconds
- Database query time: 20 seconds/table
- Memory usage: 2GB peak
```

### Performance Regression Detection

Set up alerts for performance regressions.

**Strategies:**
- Alert if profiling time exceeds baseline by 50%
- Alert if memory usage exceeds thresholds
- Alert on error rate increases
- Monitor database load during profiling

---

## Related Documentation

- [Best Practices Guide](BEST_PRACTICES.md) - General best practices
- [Sampling Guide](PARTITION_SAMPLING.md) - Detailed sampling strategies
- [Parallelism Guide](PARALLELISM_AND_BATCHING.md) - Parallel execution details
- [Incremental Profiling Guide](INCREMENTAL_PROFILING.md) - Incremental profiling details


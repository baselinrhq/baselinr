# Prometheus Metrics Integration

ProfileMesh now includes Prometheus metrics exporting for comprehensive monitoring and observability.

## Features

The metrics system provides:

- **Profiling metrics**: Run counts, duration histograms, row/column counts
- **Drift detection metrics**: Drift event counts, detection duration
- **Schema change metrics**: Schema modification tracking
- **Query metrics**: Warehouse query execution times
- **Error metrics**: Error tracking by warehouse and component
- **Worker metrics**: Active worker gauge for concurrency monitoring

## Installation

Install the Prometheus client library:

```bash
pip install prometheus_client>=0.19.0
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Configuration

Add the monitoring section to your ProfileMesh config file:

```yaml
monitoring:
  enable_metrics: true  # Enable Prometheus metrics
  port: 9753            # Port for metrics HTTP server (default: 9753)
  keep_alive: true      # Keep server running after profiling completes (default: true)
```

Example: `examples/config_with_metrics.yml`

## Available Metrics

### Profiling Metrics

**`profilemesh_profile_runs_total`** (Counter)
- Total number of profiling runs
- Labels: `warehouse`, `table`, `status` (success/failed)

**`profilemesh_profile_duration_seconds`** (Histogram)
- Histogram of profile execution times in seconds
- Labels: `warehouse`, `table`
- Buckets: 0.1s, 0.5s, 1s, 2.5s, 5s, 10s, 30s, 60s, 120s, 300s

**`profilemesh_rows_profiled_total`** (Counter)
- Total number of rows profiled
- Labels: `warehouse`, `table`

**`profilemesh_columns_profiled_total`** (Counter)
- Total number of columns profiled
- Labels: `warehouse`, `table`

**`profilemesh_active_workers`** (Gauge)
- Number of currently running worker threads

### Drift Detection Metrics

**`profilemesh_drift_events_total`** (Counter)
- Total number of drift detection events
- Labels: `warehouse`, `table`, `metric`, `severity` (low/medium/high)

**`profilemesh_drift_detection_duration_seconds`** (Histogram)
- Histogram of drift detection execution times in seconds
- Labels: `warehouse`, `table`
- Buckets: 0.1s, 0.5s, 1s, 2.5s, 5s, 10s, 30s

**`profilemesh_schema_changes_total`** (Counter)
- Total number of schema change events
- Labels: `warehouse`, `table`, `change_type` (column_added/column_removed/type_changed)

### Query and Error Metrics

**`profilemesh_query_duration_seconds`** (Histogram)
- Histogram of warehouse query execution times in seconds
- Labels: `warehouse`
- Buckets: 0.01s, 0.05s, 0.1s, 0.5s, 1s, 2.5s, 5s, 10s

**`profilemesh_errors_total`** (Counter)
- Total number of errors
- Labels: `warehouse`, `error_type`, `component` (profiler/drift_detector/connector)

## Usage

### CLI Usage

Run profiling with metrics enabled:

```bash
profilemesh profile --config config_with_metrics.yml
```

The metrics server will start automatically and remain running after profiling completes (by default). Metrics will be available at:
```
http://localhost:9753/metrics
```

Press Ctrl+C to stop the metrics server and exit.

**Note**: If you want the CLI to exit immediately after profiling (e.g., in CI/CD), set `keep_alive: false` in your config:

```yaml
monitoring:
  enable_metrics: true
  port: 9753
  keep_alive: false  # Exit immediately after profiling
```

### Dagster Usage

When running in Dagster, metrics are automatically collected if enabled in your configuration. The metrics server starts when the Dagster daemon initializes.

### Accessing Metrics

Visit the metrics endpoint to see live metrics:

```bash
curl http://localhost:9753/metrics
```

Example output:

```prometheus
# HELP profilemesh_profile_runs_total Total number of profiling runs
# TYPE profilemesh_profile_runs_total counter
profilemesh_profile_runs_total{warehouse="postgres",table="public.customers",status="success"} 3.0

# HELP profilemesh_profile_duration_seconds Histogram of profile execution times in seconds
# TYPE profilemesh_profile_duration_seconds histogram
profilemesh_profile_duration_seconds_bucket{le="0.5",warehouse="postgres",table="public.customers"} 3.0
profilemesh_profile_duration_seconds_sum{warehouse="postgres",table="public.customers"} 0.42
profilemesh_profile_duration_seconds_count{warehouse="postgres",table="public.customers"} 3.0

# HELP profilemesh_drift_events_total Total number of drift detection events
# TYPE profilemesh_drift_events_total counter
profilemesh_drift_events_total{warehouse="postgres",table="customers",metric="row_count",severity="high"} 2.0

# HELP profilemesh_active_workers Number of currently running worker threads
# TYPE profilemesh_active_workers gauge
profilemesh_active_workers 0.0
```

## Integration with Prometheus

### Prometheus Configuration

Add ProfileMesh as a scrape target in your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'profilemesh'
    static_configs:
      - targets: ['localhost:9753']
    scrape_interval: 15s
```

### Grafana Dashboard

Create custom dashboards to visualize:

- Profiling throughput and latency
- Drift detection patterns over time
- Error rates by warehouse
- Active worker concurrency
- Schema change frequency

## Architecture

The metrics system is integrated at multiple layers:

1. **CLI Layer**: Starts metrics server, creates run context with metrics flag
2. **Profiling Engine**: Records profile start/complete/failed events with timing
3. **Drift Detector**: Records drift events, schema changes, and detection timing
4. **Warehouse Connectors**: Records query execution times and errors
5. **Run Context**: Propagates metrics_enabled flag through the pipeline

## Troubleshooting

### Metrics Server Won't Start

**Error**: `Failed to start metrics server on port 9753: Address already in use`

**Solution**: Another process is using port 9753. Change the port in your config:

```yaml
monitoring:
  enable_metrics: true
  port: 9754  # Use a different port
```

### No Metrics Appearing

**Check**:
1. Is `enable_metrics: true` in your config?
2. Is `prometheus_client` installed?
3. Is the metrics server running? Check logs for "Prometheus metrics server started"
4. Can you access `http://localhost:9753/metrics` in your browser?

### Import Error

**Error**: `ModuleNotFoundError: No module named 'prometheus_client'`

**Solution**: Install the Prometheus client:
```bash
pip install prometheus_client>=0.19.0
```

## Best Practices

1. **Enable in Production**: Metrics are lightweight and provide valuable observability
2. **Use Appropriate Port**: Ensure port 9753 (or your custom port) is accessible
3. **Monitor Latency**: Watch `profile_duration_seconds` histograms for performance issues
4. **Alert on Errors**: Set up alerts on `profilemesh_errors_total`
5. **Track Drift Trends**: Use drift metrics to identify data quality issues early

## Performance Impact

The metrics system has minimal overhead:

- Metric updates: ~0.001ms per operation
- HTTP server: Single background thread
- Memory: ~10-50MB for metric storage
- Network: ~1-5KB per scrape

## Future Enhancements

Planned improvements:

- [ ] Dagster-specific metrics (asset materializations, job success rates)
- [ ] Custom metric exporters (StatsD, CloudWatch, Datadog)
- [ ] Metric aggregation by environment
- [ ] SLA tracking and alerting
- [ ] Cost metrics (query costs, storage usage)

## Related Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)
- [ProfileMesh Configuration](./docs/configuration.md)

---

For questions or issues, please file a GitHub issue or contact the ProfileMesh team.


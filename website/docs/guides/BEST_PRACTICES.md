# Best Practices Guide

Recommended patterns and practices for using Baselinr effectively.

## Table of Contents

- [Configuration Best Practices](#configuration-best-practices)
- [Profiling Best Practices](#profiling-best-practices)
- [Drift Detection Best Practices](#drift-detection-best-practices)
- [Performance Best Practices](#performance-best-practices)
- [Security Best Practices](#security-best-practices)
- [Integration Best Practices](#integration-best-practices)
- [Monitoring Best Practices](#monitoring-best-practices)
- [Organization Best Practices](#organization-best-practices)

## Configuration Best Practices

### Environment-Specific Configurations

Use separate configuration files for different environments.

**Example:**
```yaml
# config/development.yml
environment: development
source:
  type: postgres
  host: localhost
  # ...
```

```yaml
# config/production.yml
environment: production
source:
  type: postgres
  host: prod-db.example.com
  # ...
```

**Best Practices:**
- Keep development and production configs separate
- Use environment variables for sensitive values
- Version control configuration templates (without secrets)
- Use secrets management for passwords and credentials

### Configuration Organization

Organize configuration logically:

```yaml
# Good: Clear structure
environment: production

# Source connection
source:
  type: postgres
  host: ${DB_HOST}
  database: ${DB_NAME}
  username: ${DB_USER}
  password: ${DB_PASSWORD}  # Use env var or secrets manager

# Storage configuration
storage:
  connection:
    type: postgres
    # ...
  results_table: baselinr_results
  runs_table: baselinr_runs

# Profiling configuration
profiling:
  tables:
    - table: customers
    - table: orders
  # ...
```

**Best Practices:**
- Group related settings together
- Use comments to document complex configurations
- Keep default values minimal (let defaults work)
- Document non-obvious configuration choices

### Environment Variables

Use environment variables for sensitive and environment-specific values.

**Example:**
```yaml
source:
  type: postgres
  host: ${BASELINR_DB_HOST}
  database: ${BASELINR_DB_NAME}
  username: ${BASELINR_DB_USER}
  password: ${BASELINR_DB_PASSWORD}
```

**Best Practices:**
- Use descriptive environment variable names with prefix
- Document required environment variables
- Provide defaults where appropriate
- Never commit secrets to version control

## Profiling Best Practices

### Table Selection

Select tables strategically based on business value.

**Best Practices:**
- Profile critical business tables first
- Focus on tables with high data quality requirements
- Include tables used for reporting and analytics
- Start with a small subset and expand gradually

**Example:**
```yaml
profiling:
  # Phase 1: Critical business tables
  tables:
    - table: customers
    - table: orders
  
  # Phase 2: Expand to related tables
  # tables:
  #   - table: order_items
  #   - table: products
```

### Sampling Strategy

Use sampling for large tables to balance accuracy and performance.

**Best Practices:**
- Sample 1-5% for very large tables (&gt;100M rows)
- Use random sampling for general purpose
- Use stratified sampling for skewed distributions
- Set `max_rows` to cap sample size

**Example:**
```yaml
profiling:
  tables:
    - table: large_table
      sampling:
        enabled: true
        method: random
        fraction: 0.01  # 1% sample
        max_rows: 1000000  # Cap at 1M rows
```

### Partition Strategy

Use partition-aware profiling for partitioned tables.

**Best Practices:**
- Use `latest` strategy for time-series data
- Use `recent_n` for rolling window analysis
- Profile full table only when necessary
- Set appropriate `recent_n` based on partition frequency

**Example:**
```yaml
profiling:
  tables:
    - table: events
      partition:
        key: event_date
        strategy: recent_n
        recent_n: 7  # Last 7 days
```

### Metrics Selection

Choose metrics based on data types and use cases.

**Best Practices:**
- Include essential metrics: `count`, `null_ratio`, `distinct_count`
- Add statistical metrics for numeric columns: `mean`, `stddev`
- Use `histogram` for distributions (but can be expensive)
- Consider data type when selecting metrics

**Example:**
```yaml
profiling:
  # Comprehensive metrics
  metrics:
    - count
    - null_count
    - null_ratio
    - distinct_count
    - unique_ratio
    - min
    - max
    - mean
    - stddev
    - histogram
```

## Drift Detection Best Practices

### Threshold Configuration

Configure thresholds based on your data characteristics and business requirements.

**Best Practices:**
- Start with default thresholds and adjust based on false positive/negative rates
- Use type-specific thresholds to reduce false positives
- Different thresholds for different metrics (e.g., more lenient for `mean`, strict for `null_ratio`)
- Test thresholds with historical data if available

**Example:**
```yaml
drift_detection:
  strategy: absolute_threshold
  absolute_threshold:
    low_threshold: 5.0
    medium_threshold: 15.0
    high_threshold: 30.0
  
  # Type-specific overrides
  enable_type_specific_thresholds: true
  type_specific_thresholds:
    numeric:
      mean:
        low: 10.0      # More lenient for means
        medium: 25.0
        high: 50.0
      null_ratio:
        low: 1.0       # Very sensitive to null changes
        medium: 5.0
        high: 10.0
```

### Baseline Strategy

Choose appropriate baseline selection strategy.

**Best Practices:**
- Use `auto` for automatic best baseline selection
- Use `last_run` for simple comparison
- Use `moving_average` for stable baseline (reduces noise)
- Use `prior_period` for time-based comparison (e.g., week-over-week)

**Example:**
```yaml
drift_detection:
  baselines:
    strategy: moving_average  # Use average of last 7 runs
    windows:
      moving_average: 7
      prior_period: 7
      min_runs: 3
```

### Monitoring Frequency

Determine appropriate profiling and drift detection frequency.

**Best Practices:**
- Profile critical tables daily or hourly
- Profile less critical tables weekly
- Run drift detection after each profiling run
- Use scheduling tools (Dagster, Airflow) for automation

**Example (Dagster):**
```python
from dagster import schedule, daily_schedule

@daily_schedule(
    job=profile_assets,
    start_date=datetime(2024, 1, 1),
    execution_timezone="UTC",
)
def daily_profiling_schedule(context):
    return {}
```

## Performance Best Practices

### Parallelism

Enable parallelism for faster profiling of multiple tables.

**Best Practices:**
- Start with 2-4 workers and scale up based on database capacity
- Monitor database load when enabling parallelism
- Use warehouse-specific limits to prevent overload
- Disable parallelism for SQLite (single writer)

**Example:**
```yaml
execution:
  max_workers: 4  # Parallel profiling
  batch_size: 10
  warehouse_limits:
    snowflake: 20    # Snowflake can handle more
    postgres: 8      # Postgres moderate concurrency
    sqlite: 1        # SQLite single writer
```

### Incremental Profiling

Enable incremental profiling to skip unchanged tables.

**Best Practices:**
- Enable for large-scale deployments
- Use change detection to skip unchanged tables
- Set appropriate TTL for metadata cache
- Monitor false negatives (unchanged tables that should be profiled)

**Example:**
```yaml
incremental:
  enabled: true
  change_detection:
    enabled: true
    metadata_table: baselinr_table_state
    snapshot_ttl_minutes: 1440  # 24 hours
```

### Cost Controls

Set cost guardrails for large-scale profiling.

**Best Practices:**
- Set `max_bytes_scanned` or `max_rows_scanned` limits
- Use sampling when limits would be exceeded
- Monitor profiling costs over time
- Adjust limits based on budget

**Example:**
```yaml
incremental:
  cost_controls:
    enabled: true
    max_bytes_scanned: 1000000000  # 1GB per run
    fallback_strategy: sample
    sample_fraction: 0.1  # 10% sample if limit exceeded
```

## Security Best Practices

### Credential Management

Never commit credentials to version control.

**Best Practices:**
- Use environment variables for credentials
- Use GitHub Secrets for CI/CD (free)
- Use platform-native secrets for production deployments
- Use separate credentials for read-only profiling vs. storage writes
- Rotate credentials regularly

**Example:**
```yaml
# Bad: Hardcoded credentials
source:
  password: mypassword123

# Good: Environment variable
source:
  password: ${BASELINR_SOURCE__PASSWORD}

# Better: Use secrets management (see SECRETS_MANAGEMENT.md)
```

📖 **For detailed secrets management guide with free options, see:** [Secrets Management Guide](../guides/SECRETS_MANAGEMENT.md)

### Network Security

Secure database connections appropriately.

**Best Practices:**
- Use SSL/TLS for database connections in production
- Restrict network access to databases
- Use VPCs or private networks when possible
- Monitor connection attempts and failures

**Example:**
```yaml
source:
  type: postgres
  host: db.example.com
  extra_params:
    sslmode: require  # Require SSL
```

### Access Control

Limit permissions to minimum required.

**Best Practices:**
- Use read-only database user for profiling
- Grant CREATE TABLE only for storage database
- Use separate users for source and storage
- Audit access regularly

## Integration Best Practices

### Dagster Integration

Leverage Dagster for orchestration and scheduling.

**Best Practices:**
- Use Dagster assets for profiling jobs
- Schedule profiling runs based on data freshness requirements
- Set up sensors for event-driven profiling
- Monitor job execution in Dagster UI

### Custom Hooks

Implement custom hooks for your alerting system.

**Best Practices:**
- Use hooks for real-time alerts on drift
- Integrate with your existing monitoring infrastructure
- Set appropriate severity filters to reduce noise
- Test hooks in development before production

**Example:**
```yaml
hooks:
  enabled: true
  hooks:
    - type: custom
      enabled: true
      module: my_hooks
      class_name: PagerDutyHook
      params:
        api_key: ${PAGERDUTY_API_KEY}
        min_severity: medium
```

### SDK Usage

Use the Python SDK for programmatic access.

**Best Practices:**
- Initialize client once and reuse
- Handle errors appropriately
- Use progress callbacks for long-running operations
- Close connections when done

**Example:**
```python
from baselinr import BaselinrClient

# Initialize once
client = BaselinrClient(config_path="config.yml")

# Profile with progress
def progress(current, total, table_name):
    print(f"Progress: {current}/{total} - {table_name}")

results = client.profile(progress_callback=progress)

# Query results
runs = client.query_runs(days=7)
status = client.get_status()
```

## Monitoring Best Practices

### Prometheus Metrics

Enable Prometheus metrics for observability.

**Best Practices:**
- Enable metrics in production
- Export to Prometheus for long-term storage
- Create dashboards for key metrics
- Set up alerts based on metrics

**Example:**
```yaml
monitoring:
  enable_metrics: true
  port: 9753
  keep_alive: true  # Keep server running
```

### Logging

Configure appropriate logging levels.

**Best Practices:**
- Use INFO level for normal operations
- Use DEBUG level for troubleshooting
- Log important events (profiling start/end, drift detected)
- Centralize logs for easier analysis

**Example:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Organization Best Practices

### Naming Conventions

Use consistent naming for tables, schemas, and environments.

**Best Practices:**
- Use clear, descriptive table names
- Organize tables into logical schemas
- Use consistent environment naming (dev/staging/prod)
- Document naming conventions

### Documentation

Document your configuration and setup.

**Best Practices:**
- Document which tables are profiled and why
- Document drift detection thresholds and rationale
- Document any custom hooks or integrations
- Keep configuration comments up to date

### Version Control

Version control configurations and related code.

**Best Practices:**
- Store configuration templates in version control
- Keep secrets separate (use .gitignore)
- Tag configurations with deployment versions
- Document configuration changes in commit messages

---

## Related Documentation

- [Configuration Reference](../reference/CONFIG_REFERENCE.md) - Complete configuration reference
- [Performance Tuning Guide](PERFORMANCE_TUNING.md) - Performance optimization
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Python SDK Guide](PYTHON_SDK.md) - SDK usage patterns


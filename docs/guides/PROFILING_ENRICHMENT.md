# Profiling Enrichment

Baselinr includes enhanced profiling capabilities that track richer data quality metrics and provide deeper insights into your data over time. These enrichment features enable better anomaly learning and drift detection.

## Overview

Profiling enrichment extends the base profiling metrics with:

- **Data Quality Metrics**: Null ratios, uniqueness ratios, approximate distinct counts, and data type inference
- **Schema Tracking**: Schema freshness, versioning, and column stability
- **Row Count Stability**: Track row count changes and trends over time
- **Column Lifecycle**: Track when columns appear, disappear, and how stable they are

All enrichment metrics are timestamped and stored with each profiling run, enabling historical analysis and anomaly learning.

## Configuration

Enrichment features are enabled by default. You can configure them in your `config.yml`:

```yaml
profiling:
  # Enable enrichment features (default: true)
  enable_enrichment: true
  
  # Enable approximate distinct count (default: true)
  enable_approx_distinct: true
  
  # Enable schema change tracking (default: true)
  enable_schema_tracking: true
  
  # Enable data type inference (default: true)
  enable_type_inference: true
  
  # Enable column stability tracking (default: true)
  enable_column_stability: true
  
  # Number of runs to use for stability calculations (default: 7)
  stability_window: 7
  
  # Sample size for type inference (default: 1000)
  type_inference_sample_size: 1000
```

## Metrics

### Column-Level Metrics

#### Null Ratio

**Metric Name**: `null_ratio`

The ratio of null values to total values in the column (0.0 to 1.0).

- Replaces the old `null_percent` metric (which was 0-100)
- To convert to percentage: `null_ratio * 100`

Example:
```json
{
  "column": "email",
  "null_ratio": 0.02,
  "null_count": 200,
  "count": 10000
}
```

#### Uniqueness Ratio

**Metric Name**: `unique_ratio`

The ratio of distinct values to total values (0.0 to 1.0).

- Replaces the old `distinct_percent` metric (which was 0-100)
- To convert to percentage: `unique_ratio * 100`
- A value of 1.0 means all values are unique
- A value close to 0.0 means many duplicates

Example:
```json
{
  "column": "user_id",
  "unique_ratio": 0.998,
  "distinct_count": 9980,
  "count": 10000
}
```

#### Approximate Distinct Count

**Metric Name**: `approx_distinct_count`

An approximate count of distinct values using database-specific functions.

- Uses `APPROX_COUNT_DISTINCT()` for Snowflake, BigQuery, and Redshift
- Falls back to exact `COUNT(DISTINCT)` for PostgreSQL, MySQL, and SQLite
- Useful for very large datasets where exact distinct count is expensive

Example:
```json
{
  "column": "user_id",
  "distinct_count": 100234,
  "approx_distinct_count": 99850
}
```

#### Data Type Inferred

**Metric Name**: `data_type_inferred`

The inferred data type from analyzing sample values.

Inferred types include:
- `boolean`: Boolean patterns (true/false, yes/no, 0/1)
- `integer`: Whole numbers
- `numeric`: Decimal numbers
- `date`: Date/timestamp patterns
- `email`: Email address patterns
- `url`: URL patterns
- `uuid`: UUID patterns
- `json`: JSON structures
- `string`: Default fallback

Example:
```json
{
  "column": "email",
  "column_type": "VARCHAR(255)",
  "data_type_inferred": "email"
}
```

This helps detect when the database column type doesn't match the actual data pattern.

#### Column Stability Score

**Metric Name**: `column_stability_score`

The ratio of runs where the column exists vs total runs (0.0 to 1.0).

- 1.0 means the column has been present in all runs
- Lower values indicate the column is frequently added/removed
- Useful for detecting unstable schemas

Example:
```json
{
  "column": "new_feature_flag",
  "column_stability_score": 0.5,
  "column_age_days": 30
}
```

#### Column Age

**Metric Name**: `column_age_days`

Number of days since the column first appeared in profiling runs.

Example:
```json
{
  "column": "created_at",
  "column_age_days": 365
}
```

#### Type Consistency Score

**Metric Name**: `type_consistency_score`

Consistency of column type across runs (1.0 if never changed, 0.0 if changed).

Example:
```json
{
  "column": "age",
  "column_type": "INTEGER",
  "type_consistency_score": 1.0
}
```

### Table-Level Metrics

These metrics are stored in the run metadata (accessible via `ProfilingResult.metadata`):

#### Row Count Change

**Metadata Key**: `row_count_change`

Absolute change in row count from the previous run.

Example:
```json
{
  "row_count": 1000000,
  "row_count_change": 5000,
  "row_count_change_percent": 0.5
}
```

#### Row Count Change Percent

**Metadata Key**: `row_count_change_percent`

Percentage change in row count from the previous run.

#### Row Count Stability Score

**Metadata Key**: `row_count_stability_score`

Coefficient of variation-based stability score (0.0 to 1.0, higher is more stable).

Calculated over the last N runs (configurable via `stability_window`).

#### Row Count Trend

**Metadata Key**: `row_count_trend`

Direction of row count trend: `"increasing"`, `"decreasing"`, or `"stable"`.

#### Schema Freshness

**Metadata Key**: `schema_freshness`

ISO timestamp of the last schema modification (when columns were added/removed or types changed).

Example:
```json
{
  "schema_freshness": "2025-11-16T10:00:00Z",
  "schema_version": 3
}
```

#### Schema Version

**Metadata Key**: `schema_version`

Incrementing version number that increases each time the schema changes.

#### Column Count Change

**Metadata Key**: `column_count_change`

Net change in column count (added - removed).

## Extended Profile Format

With enrichment enabled, the profile output includes:

```json
{
  "column": "email",
  "column_type": "VARCHAR(255)",
  "data_type_inferred": "email",
  "null_ratio": 0.02,
  "distinct_count": 100234,
  "approx_distinct_count": 99850,
  "unique_ratio": 0.998,
  "min": null,
  "max": null,
  "column_stability_score": 1.0,
  "column_age_days": 365,
  "type_consistency_score": 1.0,
  "profiled_at": "2025-11-16T10:00:00Z"
}
```

Table-level enrichment metrics are stored in `ProfilingResult.metadata`:

```json
{
  "row_count": 1000000,
  "row_count_change": 5000,
  "row_count_change_percent": 0.5,
  "row_count_stability_score": 0.95,
  "row_count_trend": "increasing",
  "schema_freshness": "2025-11-16T10:00:00Z",
  "schema_version": 3,
  "column_count": 25,
  "column_count_change": 1
}
```

## Migration from Old Metrics

If you were using the old metric names, update your queries and code:

### `null_percent` → `null_ratio`

**Before:**
```python
null_percent = 2.5  # 2.5%
```

**After:**
```python
null_ratio = 0.025  # 0.025 (2.5%)
# To get percentage: null_ratio * 100
```

### `distinct_percent` → `unique_ratio`

**Before:**
```python
distinct_percent = 99.8  # 99.8%
```

**After:**
```python
unique_ratio = 0.998  # 0.998 (99.8%)
# To get percentage: unique_ratio * 100
```

## Performance Considerations

### Approximate Distinct Count

- Uses database-native approximate functions where available (Snowflake, BigQuery, Redshift)
- Falls back to exact `COUNT(DISTINCT)` for other databases
- Significantly faster for very large datasets

### Type Inference

- Samples up to `type_inference_sample_size` non-null values (default: 1000)
- Analysis is done in-memory on the sample
- Fast and efficient for most use cases

### Stability Calculations

- Queries historical runs (limited to `stability_window` runs, default: 7)
- Can be disabled if performance is a concern
- Results are cached in the current run metadata

## Use Cases

### Anomaly Learning

Use enrichment metrics to learn expected ranges:

```python
# Track null_ratio over time
null_ratios = [run.metadata.get("null_ratio") for run in historical_runs]

# Learn normal range
mean_null_ratio = statistics.mean(null_ratios)
std_null_ratio = statistics.stdev(null_ratios)

# Flag anomalies
if current_null_ratio > mean_null_ratio + 2 * std_null_ratio:
    alert("Anomalous null ratio detected")
```

### Schema Change Detection

Monitor schema stability:

```python
# Check schema freshness
last_schema_change = result.metadata.get("schema_freshness")
if last_schema_change:
    days_since_change = (datetime.now() - parse_date(last_schema_change)).days
    if days_since_change < 7:
        alert("Recent schema changes detected")
```

### Data Quality Monitoring

Track data quality trends:

```python
# Monitor uniqueness
unique_ratio = column_metrics.get("unique_ratio")
if unique_ratio < 0.5:
    alert("Low uniqueness detected - possible data quality issue")
```

## Examples

See [examples/config_enrichment.yml](../examples/config_enrichment.yml) for a complete configuration example with all enrichment features enabled.

## API Reference

### ProfilingConfig

```python
class ProfilingConfig:
    enable_enrichment: bool = True
    enable_approx_distinct: bool = True
    enable_schema_tracking: bool = True
    enable_type_inference: bool = True
    enable_column_stability: bool = True
    stability_window: int = 7
    type_inference_sample_size: int = 1000
```

### MetricCalculator

The `MetricCalculator` class automatically includes enrichment metrics when `enable_enrichment=True`.

### ResultWriter

The `ResultWriter.calculate_and_write_enrichment_metrics()` method calculates and stores enrichment metrics during result writing.

## Troubleshooting

### Enrichment Metrics Not Appearing

1. Check that `enable_enrichment: true` in your config
2. Verify storage is accessible (required for stability calculations)
3. Check logs for any warnings about failed enrichment calculations

### Performance Issues

1. Reduce `type_inference_sample_size` if type inference is slow
2. Reduce `stability_window` if stability calculations are slow
3. Disable specific enrichment features if not needed

### Schema Version Not Incrementing

Schema version is calculated based on detected schema changes. If columns/types haven't changed between runs, the version won't increment.

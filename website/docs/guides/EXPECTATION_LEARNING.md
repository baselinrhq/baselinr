# Expectation Learning in Baselinr

Baselinr can automatically learn expected metric ranges from historical profiling data, enabling automatic outlier detection without requiring explicit thresholds.

## Overview

**Expectation Learning** is a feature that automatically computes expected statistical ranges for metrics based on historical profiling runs. This complements the existing **baseline** system by providing pre-computed statistical models that can detect anomalies.

### Expectations vs Baselines

**Baselines** (existing system):
- Selected dynamically during drift detection (e.g., "last run", "moving average")
- Single value or simple aggregation used as a reference point
- Purpose: answer **"is the current value different from the baseline?"**
- Computed on-demand based on drift detection strategy
- Used for detecting changes over time

**Learned Expectations** (new system):
- Pre-computed and persistently stored statistical models
- Rich statistical properties: expected mean/variance, control limits, learned distributions, categorical frequencies
- Purpose: answer **"is this value within the expected normal range?"**
- Continuously updated as new profiling runs complete
- Used for automatic outlier detection without explicit thresholds
- Independent of drift detection configuration

**Key Difference**: Baselines help detect **changes** ("this value changed from last week"), while expectations help detect **anomalies** ("this value is outside the 3-sigma normal range"). They complement each other - a value can both drift from baseline AND be within expected range, or vice versa.

## Configuration

Expectation learning is **opt-in** and disabled by default. Enable it in your storage configuration:

```yaml
storage:
  connection:
    type: postgres
    host: localhost
    database: baselinr_db
  
  # Expectation learning configuration
  enable_expectation_learning: true
  learning_window_days: 30        # Learn from last 30 days (default: 30)
  min_samples: 5                   # Require at least 5 runs (default: 5)
  ewma_lambda: 0.2                 # EWMA smoothing parameter (default: 0.2)
```

### Configuration Options

- **`enable_expectation_learning`** (bool, default: `false`)
  - Enable automatic learning of expected metric ranges
  - Set to `true` to enable expectation learning

- **`learning_window_days`** (int, default: `30`)
  - Historical window in days for learning expectations
  - Only profiling runs within this window are used for learning
  - Longer windows provide more stable expectations but may include outdated patterns
  - Shorter windows adapt faster to changes but may be less reliable

- **`min_samples`** (int, default: `5`)
  - Minimum number of historical runs required before learning expectations
  - If fewer runs are available, expectations will not be learned for that metric
  - Lower values allow learning with less history but may be less reliable
  - Recommended: 5-10 for stable expectations

- **`ewma_lambda`** (float, default: `0.2`)
  - Exponentially Weighted Moving Average smoothing parameter
  - Range: 0 &lt; lambda &le; 1
  - Lower values (e.g., 0.1) give more weight to older data (smoother)
  - Higher values (e.g., 0.3) give more weight to recent data (more reactive)
  - Used for computing EWMA-based expectations

## How Expectations are Learned

After each profiling run completes, if expectation learning is enabled, Baselinr will:

1. **Query Historical Data**: Retrieve metric values from previous profiling runs within the configured window
2. **Check Sample Size**: Ensure sufficient samples are available (>= `min_samples`)
3. **Compute Statistics**: Calculate expected mean, variance, standard deviation, min, max
4. **Compute Control Limits**: Calculate Shewhart 3-sigma control limits (mean ± 3σ)
5. **Learn Distribution**: Detect if values follow a normal distribution (heuristic-based)
6. **Learn Categorical Frequencies**: For categorical columns, learn expected frequency distributions
7. **Store Expectations**: Save learned expectations to the `baselinr_expectations` table

### Supported Metrics

Expectations are learned for numeric metrics:
- `mean` - Expected mean value
- `stddev` - Expected standard deviation
- `count` - Expected row count
- `null_ratio` - Expected null percentage
- `unique_ratio` - Expected uniqueness ratio

### What Gets Learned

For each metric, the following information is stored:

- **Expected Statistics**:
  - Mean, variance, standard deviation
  - Min and max observed values

- **Control Limits**:
  - Lower Control Limit (LCL) and Upper Control Limit (UCL)
  - Typically computed using Shewhart 3-sigma method: mean ± 3 × stddev

- **Distribution Information**:
  - Distribution type (normal, empirical)
  - Distribution parameters (mean, stddev, etc.)

- **Categorical Distributions** (for categorical columns):
  - Expected frequency for each category value

- **EWMA** (if sufficient samples):
  - Exponentially Weighted Moving Average value

## Automatic Updates

Expectations are automatically updated after each profiling run if:
- Expectation learning is enabled
- Sufficient historical data is available (>= `min_samples`)
- The metric exists in the current profiling run

Expectations are recalculated from scratch using all available historical data within the window, ensuring they stay current with data patterns.

## Using Expectations for Outlier Detection

*(Future feature - expectations are currently learned but not yet used for automatic outlier detection)*

In future versions, learned expectations will be used to automatically flag outliers without requiring explicit thresholds. For example:
- Values outside the 3-sigma control limits
- Categorical values with unexpected frequencies
- Values that don't match the learned distribution

## Troubleshooting

### Expectations Not Being Learned

**Symptom**: No expectations appear in the database after profiling runs.

**Possible Causes**:
1. **Learning disabled**: Check that `enable_expectation_learning: true` in storage config
2. **Insufficient samples**: Not enough historical runs (need >= `min_samples`)
   - Solution: Wait for more profiling runs, or reduce `min_samples`
3. **Window too short**: Historical window doesn't contain enough runs
   - Solution: Increase `learning_window_days`

**Check logs**: Look for debug messages like:
```
Insufficient samples for table.column.metric: 3 < 5
```

### Expectations Not Updating

**Symptom**: Expectations exist but don't change after new profiling runs.

**Possible Causes**:
1. **Learning disabled**: Check configuration
2. **Errors during learning**: Check logs for warnings
3. **Metric not in current run**: If a metric doesn't appear in the current run, expectations won't update

**Check logs**: Look for warnings like:
```
Failed to learn expectations for table.column.metric: ...
```

### Control Limits Seem Wrong

**Symptom**: Control limits (LCL/UCL) don't match expected ranges.

**Possible Causes**:
1. **High variance in historical data**: Control limits are computed as mean ± 3σ
   - High variance = wider limits
   - This may be correct if your data is naturally variable
2. **Limited historical data**: With few samples, statistics may be unreliable
   - Solution: Ensure >= 10 samples for more reliable limits
3. **Non-normal distribution**: Shewhart limits assume normal distribution
   - Baselinr detects distribution type, but limits are still computed using standard deviation

**Recommendation**: Review the `expected_stddev` and `distribution_type` in expectations to understand the data characteristics.

## Example Configuration

### Basic Setup

```yaml
storage:
  connection:
    type: postgres
    host: localhost
    database: baselinr_db
    username: baselinr
    password: secret
  
  enable_expectation_learning: true
```

### Advanced Setup

```yaml
storage:
  connection:
    type: snowflake
    account: myaccount
    database: BASELINR_DB
    warehouse: COMPUTE_WH
  
  # Expectation learning with custom parameters
  enable_expectation_learning: true
  learning_window_days: 60        # Use 60 days of history
  min_samples: 10                  # Require 10 runs before learning
  ewma_lambda: 0.15                # More conservative smoothing
```

### Per-Table Configuration

*(Note: Currently learning applies to all tables. Per-table configuration may be added in future versions.)*

## Database Schema

Expectations are stored in the `baselinr_expectations` table. Key fields:

- `table_name`, `schema_name`, `column_name`, `metric_name` - Identifiers
- `expected_mean`, `expected_stddev`, `expected_min`, `expected_max` - Statistics
- `lower_control_limit`, `upper_control_limit` - Control limits
- `distribution_type`, `distribution_params` - Distribution information
- `category_distribution` - Categorical frequencies (JSON)
- `sample_size`, `learning_window_days` - Metadata
- `last_updated` - Last update timestamp

Query expectations:
```sql
SELECT * FROM baselinr_expectations
WHERE table_name = 'users'
AND column_name = 'age'
AND metric_name = 'mean';
```

## Migration

To enable expectation learning on an existing Baselinr installation:

1. **Run migration** to create the expectations table:
   ```bash
   baselinr migrate
   ```

2. **Update configuration** to enable learning:
   ```yaml
   storage:
     enable_expectation_learning: true
   ```

3. **Profile your tables** - expectations will be learned automatically after sufficient runs

## Best Practices

1. **Start with defaults**: Use default configuration initially, then tune based on your data patterns
2. **Monitor sample sizes**: Ensure you have enough historical data before relying on expectations
3. **Review control limits**: Periodically check if control limits make sense for your data
4. **Combine with baselines**: Use both baselines and expectations for comprehensive monitoring
5. **Window size**: Match `learning_window_days` to your data update frequency
   - Daily updates: 30 days
   - Weekly updates: 90 days
   - Monthly updates: 180 days

## Related Documentation

- [Drift Detection Guide](DRIFT_DETECTION.md) - Understanding baselines and drift detection
- [Profiling Enrichment](PROFILING_ENRICHMENT.md) - Other enrichment features
- [Architecture: Expectation Learning](../architecture/EXPECTATION_LEARNING.md) - Technical details


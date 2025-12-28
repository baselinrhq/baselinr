# Anomaly Detection in Baselinr

Baselinr automatically detects outliers and seasonal anomalies in profiling metrics using learned expectations as baselines, enabling proactive monitoring without manual threshold configuration.

## Overview

**Anomaly Detection** automatically identifies unusual metric values that deviate significantly from learned expected ranges. This complements drift detection by flagging outliers even when they don't represent drift from recent baselines.

### How Anomaly Detection Works

Anomaly detection uses **learned expectations** (see [Expectation Learning](EXPECTATION_LEARNING.md)) as baselines:

1. **Requires Learned Expectations**: Anomaly detection only runs for metrics where expectations have been learned (from historical profiling data)

2. **Multiple Detection Methods**: Uses various statistical methods to detect different types of anomalies:
   - **Control Limits**: Shewhart 3-sigma limits from expectations
   - **IQR (Interquartile Range)**: Detects outliers using quartile-based bounds
   - **MAD (Median Absolute Deviation)**: Robust outlier detection using median-based statistics
   - **EWMA (Exponentially Weighted Moving Average)**: Detects deviations from expected trends
   - **Trend/Seasonality**: Lightweight Prophet-style detection of seasonal anomalies
   - **Regime Shift**: Detects sudden behavioral changes in metric patterns

3. **Event Emission**: Detected anomalies are emitted as `AnomalyDetected` events via the event bus and stored in the `baselinr_events` table

4. **Automatic Categorization**: Anomalies are automatically categorized by type (row count spike, null spike, uniqueness drop, etc.)

## Configuration

Anomaly detection can be configured at multiple levels:

1. **Global configuration** (`storage` section) - Applies to all tables and columns
2. **Column-level configuration** - Per-column anomaly settings (see [Column-Level Configuration Guide](COLUMN_LEVEL_CONFIGS.md))

### Global Configuration

Anomaly detection is **opt-in** and disabled by default. Enable it in your storage configuration:

```yaml
storage:
  connection:
    type: postgres
    host: localhost
    database: baselinr_db
  
  # Anomaly detection configuration
  enable_anomaly_detection: true
  anomaly_enabled_methods:
    - control_limits
    - iqr
    - mad
    - ewma
    - seasonality
    - regime_shift
  anomaly_iqr_threshold: 1.5          # IQR multiplier (default: 1.5)
  anomaly_mad_threshold: 3.0           # MAD threshold (default: 3.0)
  anomaly_ewma_deviation_threshold: 2.0 # EWMA stddevs (default: 2.0)
  anomaly_seasonality_enabled: true    # Enable seasonality detection
  anomaly_regime_shift_enabled: true   # Enable regime shift detection
  anomaly_regime_shift_window: 3       # Recent runs for regime shift (default: 3)
  anomaly_regime_shift_sensitivity: 0.05 # P-value threshold (default: 0.05)
```

### Column-Level Configuration

For fine-grained control, configure anomaly detection per column in ODCS contracts:

```yaml
# contracts/orders.odcs.yaml
kind: DataContract
apiVersion: v3.1.0
id: orders_contract
dataset:
  - name: orders
    physicalName: public.orders
    columns:
      - column: amount
customProperties:
  - property: baselinr.anomaly.orders.amount
    value:
      enabled: true
      methods: [control_limits, iqr, mad]
      thresholds:
        iqr_threshold: 2.0
        mad_threshold: 3.5
  - property: baselinr.anomaly.orders.order_date
    value:
      enabled: true
      methods: [seasonality, regime_shift]
  - property: baselinr.anomaly.orders.metadata
    value:
      enabled: false  # Skip anomaly detection
```

**Important**: 
- Column-level anomaly detection configurations should be defined in ODCS contracts using customProperties
- Column-level anomaly detection requires that the column was profiled. If profiling is disabled for a column, anomaly detection is automatically skipped for that column.

**See Also**: [Column-Level Configuration Guide](COLUMN_LEVEL_CONFIGS.md) for complete documentation on column-level configurations for profiling, drift, and anomaly detection.

### Configuration Options

- **`enable_anomaly_detection`** (bool, default: `false`)
  - Enable automatic anomaly detection using learned expectations
  - Requires `enable_expectation_learning: true` to be effective

- **`anomaly_enabled_methods`** (list, default: all methods)
  - List of detection methods to enable
  - Options: `control_limits`, `iqr`, `mad`, `ewma`, `seasonality`, `regime_shift`
  - Disable methods that aren't relevant to your use case

- **`anomaly_iqr_threshold`** (float, default: `1.5`)
  - IQR multiplier for outlier detection
  - Standard IQR uses 1.5 (flags values outside [Q1 - 1.5×IQR, Q3 + 1.5×IQR])
  - Lower values = more sensitive (detects more anomalies)
  - Higher values = less sensitive (fewer false positives)

- **`anomaly_mad_threshold`** (float, default: `3.0`)
  - Modified z-score threshold for MAD detection
  - Flags values with |modified_z_score| > threshold
  - Lower values = more sensitive

- **`anomaly_ewma_deviation_threshold`** (float, default: `2.0`)
  - Number of standard deviations for EWMA-based detection
  - Compares current value to EWMA-based prediction
  - Lower values = more sensitive

- **`anomaly_seasonality_enabled`** (bool, default: `true`)
  - Enable trend and seasonality-based anomaly detection
  - Detects anomalies after removing trend and seasonal patterns
  - Useful for metrics with weekly/monthly patterns

- **`anomaly_regime_shift_enabled`** (bool, default: `true`)
  - Enable regime shift detection
  - Detects sudden behavioral changes in metric patterns
  - Compares recent runs vs historical baseline

- **`anomaly_regime_shift_window`** (int, default: `3`)
  - Number of recent runs to compare for regime shift detection
  - Larger windows = more stable but slower to detect changes

- **`anomaly_regime_shift_sensitivity`** (float, default: `0.05`)
  - P-value threshold for statistical significance
  - Lower values = more sensitive (smaller changes detected)

## Detection Methods

### Control Limits (Shewhart)

Uses 3-sigma control limits from learned expectations:
- **Lower Control Limit (LCL)**: `expected_mean - 3 × expected_stddev`
- **Upper Control Limit (UCL)**: `expected_mean + 3 × expected_stddev`
- **Detection**: Flags values outside [LCL, UCL]

**Best for**: Metrics with stable distributions, general outlier detection

**Example**: If expected mean = 30.0 and stddev = 5.0, LCL = 15.0, UCL = 45.0. Value of 50.0 would be flagged.

### IQR (Interquartile Range)

Detects outliers using quartile-based bounds:
- Calculates Q1 (25th percentile) and Q3 (75th percentile) from historical data
- **Lower Bound**: `Q1 - threshold × IQR`
- **Upper Bound**: `Q3 + threshold × IQR`
- **Detection**: Flags values outside bounds

**Best for**: Non-normal distributions, robust outlier detection

**Example**: With Q1=20, Q3=40, IQR=20, threshold=1.5: bounds are [10, 50]. Value of 60 would be flagged.

### MAD (Median Absolute Deviation)

Robust outlier detection using median-based statistics:
- Calculates median and MAD from historical data
- **Modified Z-Score**: `0.6745 × (value - median) / MAD`
- **Detection**: Flags values with |modified_z_score| > threshold

**Best for**: Non-normal distributions, metrics with outliers in historical data

**Example**: With median=30, MAD=5, threshold=3.0: value of 50 has z-score ~2.7 (flagged if threshold=2.0).

### EWMA (Exponentially Weighted Moving Average)

Detects deviations from expected EWMA trend:
- Uses EWMA value from learned expectations
- Compares current value to EWMA-based prediction
- **Detection**: Flags if deviation > threshold × stddev

**Best for**: Metrics with trends, detecting gradual shifts

**Example**: If EWMA=30.0, stddev=5.0, threshold=2.0: flags if current value differs by >10 from EWMA.

### Trend/Seasonality Detection

Lightweight Prophet-style detection of seasonal anomalies:
- Extracts trend using moving average
- Detects weekly/monthly seasonal patterns
- Removes trend and seasonality to detect anomalies in residuals
- **Detection**: Flags if detrended/deseasonalized value exceeds threshold

**Best for**: Metrics with strong seasonal patterns (daily/weekly cycles)

**Example**: If weekday mean=100 and weekend mean=150, detects if a weekday value is 140 (unusually high for weekday).

### Regime Shift Detection

Detects sudden behavioral changes:
- Compares recent runs (last N) vs historical baseline
- Uses statistical tests (t-test or simple comparison)
- **Detection**: Flags if significant shift detected (p-value < sensitivity)

**Best for**: Detecting structural changes, sudden shifts in data patterns

**Example**: If historical mean=30 and recent 3 runs average=45, detects as regime shift.

## Anomaly Types

Anomalies are automatically categorized by type:

- **`iqr_deviation`**: Outlier detected via IQR method
- **`mad_deviation`**: Outlier detected via MAD method
- **`ewma_outlier`**: Deviation from EWMA trend
- **`control_limit_breach`**: Value outside control limits
- **`seasonal_anomaly`**: Anomaly after removing seasonal patterns
- **`trend_anomaly`**: Anomaly in trend component
- **`regime_shift`**: Sudden behavioral change detected
- **`row_count_spike`**: Unusual increase in row count
- **`row_count_dip`**: Unusual decrease in row count
- **`freshness_delay`**: Increasing schema freshness delays
- **`categorical_shift`**: Shift in categorical value distribution
- **`uniqueness_drop`**: Significant drop in uniqueness ratio
- **`null_spike`**: Sudden increase in null ratio (e.g., >90%)

## Example Anomaly Scenarios

### Row Count Spike

**Scenario**: A table suddenly has 3× the normal row count.

**Detection**:
- Control limits method flags if count > UCL
- IQR method flags if count is outside IQR bounds
- Automatically categorized as `row_count_spike`

**Action**: Investigate if this is expected (e.g., data migration) or indicates a problem.

### Null Spike

**Scenario**: A column suddenly becomes 90% null.

**Detection**:
- Control limits method flags if null_ratio > 0.9
- Automatically categorized as `null_spike`

**Action**: Check for data pipeline issues, schema changes, or data quality problems.

### Uniqueness Drop

**Scenario**: A previously unique column suddenly has many duplicates.

**Detection**:
- Detects if unique_ratio drops significantly (&lt;50% of expected)
- Automatically categorized as `uniqueness_drop`

**Action**: Investigate data quality, duplicate insertion, or schema issues.

### Seasonal Anomaly

**Scenario**: A metric normally follows a weekly pattern, but Tuesday shows Monday-level values.

**Detection**:
- Trend/seasonality detector removes weekly pattern
- Flags if detrended value is anomalous for that day of week

**Action**: Check for day-specific issues (e.g., Monday holiday affecting Tuesday).

### Regime Shift

**Scenario**: A metric's mean shifts from 30 to 45 over 3 runs.

**Detection**:
- Regime shift detector compares recent runs vs historical baseline
- Statistical test indicates significant shift

**Action**: Investigate if this is expected (e.g., business change) or indicates a problem.

## Integration with Events

Anomalies are emitted as `AnomalyDetected` events and stored in `baselinr_events`:

```python
event = AnomalyDetected(
    event_type="AnomalyDetected",
    timestamp=datetime.utcnow(),
    table="users",
    column="age",
    metric="mean",
    anomaly_type="control_limit_breach",
    expected_value=30.0,
    actual_value=50.0,
    severity="high",
    detection_method="control_limits",
    metadata={...}
)
```

You can configure hooks to process these events (see [Events and Hooks](../architecture/EVENTS_AND_HOOKS.md)):

```yaml
hooks:
  enabled: true
  hooks:
    - type: logging
      log_level: WARNING  # Log anomalies at WARNING level
    - type: slack
      webhook_url: https://hooks.slack.com/...
      severity_filter: [medium, high]  # Only alert on medium/high severity
```

## Troubleshooting

### No Anomalies Detected

**Possible causes**:
1. Anomaly detection is disabled: Check `enable_anomaly_detection: true`
2. No learned expectations: Ensure `enable_expectation_learning: true` and sufficient historical data exists
3. Values are within expected ranges: This may be normal

**Solution**: Enable expectation learning and wait for enough historical runs (default: 5).

### Too Many False Positives

**Possible causes**:
1. Thresholds too sensitive (low values)
2. Metrics have high natural variance
3. Insufficient historical data for stable expectations

**Solution**:
- Increase thresholds (`anomaly_iqr_threshold`, `anomaly_mad_threshold`, etc.)
- Disable specific methods that are too sensitive
- Increase `learning_window_days` or `min_samples` for more stable expectations

### Too Few Anomalies Detected

**Possible causes**:
1. Thresholds too high (not sensitive enough)
2. Anomalies are not significant enough to trigger detection
3. Wrong detection methods enabled

**Solution**:
- Decrease thresholds
- Enable additional detection methods
- Check if expectations are too broad (may need to adjust learning parameters)

## Best Practices

1. **Enable Expectation Learning First**: Anomaly detection requires learned expectations. Enable expectation learning and wait for sufficient history before enabling anomaly detection.

2. **Start with Control Limits**: Control limits are the most straightforward method. Enable other methods as needed.

3. **Tune Thresholds Gradually**: Start with defaults and adjust based on your data characteristics.

4. **Monitor Anomaly Events**: Set up alerting hooks to be notified of anomalies, especially high-severity ones.

5. **Review Regularly**: Periodically review detected anomalies to tune thresholds and understand patterns.

6. **Combine with Drift Detection**: Anomaly detection complements drift detection - use both for comprehensive monitoring.

## Related Documentation

- [Expectation Learning](EXPECTATION_LEARNING.md) - Learn expected metric ranges
- [Events and Hooks](../architecture/EVENTS_AND_HOOKS.md) - Configure anomaly alerts
- [Drift Detection](DRIFT_DETECTION.md) - Compare against baselines
- [Architecture: Anomaly Detection](../architecture/ANOMALY_DETECTION.md) - Technical details


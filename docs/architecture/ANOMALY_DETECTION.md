# Anomaly Detection Architecture

Technical architecture documentation for the anomaly detection system in Baselinr.

## Overview

The anomaly detection system automatically identifies outliers and seasonal anomalies in profiling metrics using learned expectations as baselines. It supports multiple detection methods including IQR, MAD, EWMA, trend/seasonality decomposition, and regime shift detection.

## System Design

### High-Level Flow

```
Profiling Run Complete
    ↓
ResultWriter.write_results()
    ↓
_learn_expectations() [if enabled]
    ↓
_detect_anomalies() [if enabled]
    ↓
For each column + numeric metric:
    ↓
AnomalyDetector.detect_anomalies()
    ↓
Retrieve learned expectation from ExpectationStorage
    ↓
If expectation exists:
    ↓
Run enabled detection methods:
    - Control limits check (from expectation)
    - IQR detection (from historical data)
    - MAD detection (from historical data)
    - EWMA detection (from expectation)
    - Trend/seasonality detection (from historical series)
    - Regime shift detection (from historical data)
    ↓
Aggregate results
    ↓
Categorize anomalies by type
    ↓
Emit AnomalyDetected events via EventBus
    ↓
Store in baselinr_events table (via SQLEventHook)
```

### Components

#### 1. AnomalyDetector (`baselinr/anomaly/detector.py`)

Main orchestrator that coordinates multiple detection methods.

**Key Methods**:
- `detect_anomalies()` - Main entry point, orchestrates detection
- `_check_control_limits()` - Checks against control limits from expectations
- `_get_historical_metrics()` - Queries historical metric values for IQR/MAD
- `_get_historical_series()` - Queries time-series data for trend/seasonality
- `_categorize_anomaly()` - Maps anomalies to specific types (row_count_spike, etc.)
- `emit_anomaly_events()` - Emits events via EventBus

**Design Decisions**:
- Requires learned expectations to exist (returns early if not found)
- Runs multiple detection methods in parallel (where possible)
- Aggregates results from all methods
- Uses expectations as baselines (control limits, EWMA values)
- Falls back to raw historical data for methods that need distributions (IQR, MAD)

#### 2. Detection Methods (`baselinr/anomaly/detection_methods.py`)

Individual detection algorithms implemented as separate classes.

**IQRDetector**:
- Calculates Q1 (25th percentile) and Q3 (75th percentile) from historical values
- Computes IQR = Q3 - Q1
- Flags values outside [Q1 - threshold×IQR, Q3 + threshold×IQR]
- Best for: Non-normal distributions, robust outlier detection

**MADDetector**:
- Calculates median and MAD (Median Absolute Deviation) from historical values
- Computes modified z-score = 0.6745 × (value - median) / MAD
- Flags values with |modified_z_score| > threshold
- Best for: Non-normal distributions, metrics with outliers in history

**EWMADetector**:
- Uses EWMA value from `LearnedExpectation`
- Compares current value to EWMA-based prediction
- Uses `expected_stddev` for threshold calculation
- Flags if deviation > threshold × stddev
- Best for: Metrics with trends, detecting gradual shifts

**TrendSeasonalityDetector**:
- Extracts trend using simple moving average (configurable window)
- Detects weekly/monthly seasonal patterns
- Removes trend and seasonality to get residuals
- Flags if detrended/deseasonalized value exceeds threshold
- Lightweight heuristic-based (no optimization routines)
- Best for: Metrics with strong seasonal patterns

**RegimeShiftDetector**:
- Compares recent window (last N runs) vs historical baseline
- Options:
  - Statistical test: Two-sample t-test approximation (Welch's)
  - Simple comparison: Mean shift > threshold × stddev
- Flags if significant shift detected
- Best for: Detecting sudden behavioral changes

#### 3. AnomalyResult (`baselinr/anomaly/detector.py`)

Dataclass representing a detected anomaly.

**Fields**:
- `anomaly_type`: Enum (IQR_DEVIATION, CONTROL_LIMIT_BREACH, etc.)
- `table_name`, `column_name`, `metric_name`: Identity
- `expected_value`, `actual_value`: Comparison values
- `deviation_score`: Normalized score (0-1)
- `severity`: "low", "medium", "high"
- `detection_method`: Which method detected it
- `metadata`: Additional context (e.g., Q1/Q3, trend info)

#### 4. Event System Integration

Anomalies are emitted as `AnomalyDetected` events via the EventBus:

```python
AnomalyDetected(
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

Events are automatically stored in `baselinr_events` table via existing hooks (SQLEventHook, SnowflakeEventHook).

#### 5. ResultWriter Integration (`baselinr/storage/writer.py`)

Integration point where anomaly detection is triggered after profiling.

**Integration**:
- Called after `_learn_expectations()` completes
- Only executes if `config.enable_anomaly_detection` is True
- Iterates through columns and numeric metrics
- Handles errors gracefully (logs warning, continues)
- Doesn't block profiling completion if detection fails

**Code Flow**:
```python
def _detect_anomalies(self, result: ProfilingResult):
    detector = AnomalyDetector(...)
    for column_data in result.columns:
        for metric_name in numeric_metrics:
            anomalies = detector.detect_anomalies(...)
            if anomalies:
                detector.emit_anomaly_events(anomalies)
```

## Detection Algorithms

### Control Limits (Shewhart)

**Algorithm**:
1. Retrieve control limits from `LearnedExpectation`
2. Check if `current_value < LCL` or `current_value > UCL`
3. Calculate deviation in stddevs: `|value - mean| / stddev`
4. Determine severity based on deviation magnitude

**Severity Mapping**:
- >3 stddevs: "high"
- >2 stddevs: "medium"
- Otherwise: "low"

**Complexity**: O(1) - Direct lookup from expectations

### IQR (Interquartile Range)

**Algorithm**:
1. Fetch historical metric values from `baselinr_results`
2. Sort values
3. Calculate Q1 (25th percentile) and Q3 (75th percentile)
4. Compute IQR = Q3 - Q1
5. Calculate bounds: [Q1 - threshold×IQR, Q3 + threshold×IQR]
6. Flag if `current_value` outside bounds

**Percentile Calculation**:
- Uses linear interpolation for fractional indices
- Handles edge cases (zero IQR, insufficient data)

**Complexity**: O(n log n) - Sorting historical values

### MAD (Median Absolute Deviation)

**Algorithm**:
1. Fetch historical metric values
2. Calculate median
3. Calculate MAD = median(|x_i - median|)
4. Compute modified z-score = 0.6745 × (value - median) / MAD
5. Flag if |modified_z_score| > threshold

**Why Modified Z-Score**:
- 0.6745 constant makes MAD comparable to stddev for normal distributions
- More robust to outliers than standard z-score

**Complexity**: O(n) - Median and MAD calculation

### EWMA (Exponentially Weighted Moving Average)

**Algorithm**:
1. Retrieve `ewma_value` and `expected_stddev` from `LearnedExpectation`
2. Calculate deviation = `current_value - ewma_value`
3. Calculate deviation_stddevs = |deviation| / stddev
4. Flag if deviation_stddevs > threshold

**Fallback**:
- If no stddev available, uses 5% of mean as threshold

**Complexity**: O(1) - Direct lookup from expectations

### Trend/Seasonality Detection

**Algorithm**:
1. Fetch historical time-series (timestamp, value pairs)
2. **Trend Extraction**: Apply simple moving average
   - Window size: configurable (default: 7)
   - Trend = mean of windowed values
3. **Deseasonalize**: Calculate residuals = values - trend
4. **Seasonality Detection**:
   - Extract day-of-week for weekly seasonality
   - Group residuals by day-of-week
   - Calculate mean/stddev per day
   - Expected residual = mean for current day-of-week
5. **Anomaly Detection**:
   - Current residual = current_value - current_trend
   - Deviation = current_residual - expected_residual
   - Flag if deviation > threshold × residual_stddev

**Why Lightweight**:
- No optimization routines (unlike full Prophet)
- Uses simple moving average instead of exponential smoothing
- Heuristic-based seasonality detection

**Complexity**: O(n) - Single pass through historical series

### Regime Shift Detection

**Algorithm**:
1. Fetch historical metric values
2. Split into recent window (last N runs) and baseline (remaining)
3. **Statistical Test Option**:
   - Calculate means: recent_mean, baseline_mean
   - Calculate variances: recent_var, baseline_var
   - Pooled standard error = sqrt(recent_var/n1 + baseline_var/n2)
   - t-statistic = |recent_mean - baseline_mean| / pooled_se
   - Critical t-value based on sensitivity (p-value threshold)
   - Flag if t-stat > critical_t
4. **Simple Comparison Option**:
   - Mean shift = |recent_mean - baseline_mean|
   - Threshold = 2.0 × baseline_stddev
   - Flag if mean_shift > threshold

**Statistical Test**:
- Uses Welch's t-test approximation (two-sample, unequal variances)
- Normal approximation for critical t-values

**Complexity**: O(n) - Mean and variance calculation

## Integration Points

### With Expectation Learning

Anomaly detection depends on expectation learning:

1. **Prerequisite**: Learned expectations must exist
2. **Baseline Usage**: Uses expectations for control limits and EWMA
3. **Complementary**: Anomalies are detected after expectations are learned/updated

### With Event System

Anomalies are integrated into the existing event infrastructure:

1. **Event Emission**: `AnomalyDetected` events emitted via EventBus
2. **Storage**: Events stored in `baselinr_events` table (via hooks)
3. **Consistency**: Same pattern as drift detection events

### With Drift Detection

Anomaly detection complements drift detection:

1. **Different Purpose**: Anomalies detect outliers, drift detects changes
2. **Different Baselines**: Anomalies use expectations, drift uses baselines
3. **Complementary**: Both can detect issues, but from different perspectives

## Performance Considerations

### Database Queries

**Historical Data Fetching**:
- IQR/MAD: Fetches all historical values for metric (window: 90 days default)
- Trend/Seasonality: Fetches time-series with timestamps
- Regime Shift: Fetches historical values

**Optimization Strategies**:
- Indexes on `baselinr_results` (dataset_name, column_name, metric_name, profiled_at)
- Window limiting (90 days default) reduces query size
- Batch processing for multiple columns/metrics

### Computational Complexity

- **Control Limits**: O(1) - Direct lookup
- **EWMA**: O(1) - Direct lookup
- **IQR**: O(n log n) - Sorting
- **MAD**: O(n) - Median/MAD calculation
- **Trend/Seasonality**: O(n) - Moving average
- **Regime Shift**: O(n) - Mean/variance calculation

Where n = number of historical runs (typically 10-30).

### Caching

Currently no caching implemented. Considerations:
- Expectations are cached by ExpectationStorage (per-request)
- Historical data queries could be cached (TTL: 1 hour)
- Detection results could be cached (TTL: 5 minutes)

## Error Handling

### Graceful Degradation

All detection methods handle errors gracefully:

1. **Missing Expectations**: Returns empty list (logs debug)
2. **Insufficient Data**: Returns empty result with reason in metadata
3. **Calculation Errors**: Catches exceptions, logs warning, returns safe default
4. **Database Errors**: Catches SQL errors, logs warning, continues

### Logging

- **Debug**: Normal operations (no expectation found, insufficient data)
- **Warning**: Errors during detection (calculation failures, DB errors)
- **Info**: Significant anomalies detected

## Configuration Schema

Configuration is stored in `StorageConfig`:

```python
class StorageConfig(BaseModel):
    enable_anomaly_detection: bool = False
    anomaly_enabled_methods: List[str] = [...]
    anomaly_iqr_threshold: float = 1.5
    anomaly_mad_threshold: float = 3.0
    anomaly_ewma_deviation_threshold: float = 2.0
    anomaly_seasonality_enabled: bool = True
    anomaly_regime_shift_enabled: bool = True
    anomaly_regime_shift_window: int = 3
    anomaly_regime_shift_sensitivity: float = 0.05
```

## Future Enhancements

1. **Caching**: Cache historical data queries and detection results
2. **Machine Learning**: Add ML-based anomaly detection (Isolation Forest, etc.)
3. **Adaptive Thresholds**: Automatically tune thresholds based on false positive rate
4. **Anomaly Scoring**: Combine multiple methods into single anomaly score
5. **Trend Prediction**: Use trend models to predict expected values
6. **Multi-variate Detection**: Detect anomalies across multiple metrics simultaneously

## Testing Strategy

### Unit Tests

- **Detection Methods**: Test each method independently with known inputs
- **AnomalyDetector**: Test orchestration logic, event emission
- **Edge Cases**: Insufficient data, missing expectations, zero variance

### Integration Tests

- **End-to-End Workflow**: Learn expectations → Detect anomalies
- **Event Emission**: Verify events are emitted and stored
- **ResultWriter Integration**: Test integration with profiling workflow

### Test Coverage

- All detection methods have unit tests
- Detector orchestration has unit tests
- Integration tests cover full workflow
- Edge cases covered (insufficient data, errors, etc.)


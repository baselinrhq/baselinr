# Expectation Learning Architecture

Technical architecture documentation for the expectation learning system in Baselinr.

## Overview

The expectation learning system automatically computes expected metric ranges from historical profiling data. It learns statistical properties, control limits, distributions, and categorical frequencies to enable automatic outlier detection without explicit thresholds.

## System Design

### High-Level Flow

```
Profiling Run Complete
    ↓
ResultWriter.write_results()
    ↓
_learn_expectations() [if enabled]
    ↓
For each column + numeric metric:
    ↓
ExpectationLearner.learn_expectations()
    ↓
Query historical metrics (window_days)
    ↓
Check sample size >= min_samples
    ↓
Compute statistics, control limits, distributions
    ↓
ExpectationStorage.save_expectation()
    ↓
Store in baselinr_expectations table
```

### Components

#### 1. ExpectationLearner (`baselinr/learning/expectation_learner.py`)

Main learning engine that computes expectations from historical data.

**Key Methods**:
- `learn_expectations()` - Main entry point, orchestrates learning
- `_get_historical_metrics()` - Queries historical metric values from database
- `_compute_expected_statistics()` - Calculates mean, variance, stddev, min, max
- `_compute_control_limits()` - Computes Shewhart 3-sigma limits
- `_compute_ewma()` - Calculates Exponentially Weighted Moving Average
- `_learn_distribution()` - Detects distribution type (normal vs empirical)
- `_learn_categorical_distribution()` - Learns category frequencies

**Design Decisions**:
- Uses Python `statistics` module for calculations (reliable, standard library)
- Requires minimum 5 samples by default (configurable)
- Uses 30-day window by default (configurable)
- Skips learning gracefully if insufficient data (logs debug, continues)

#### 2. ExpectationStorage (`baselinr/learning/expectation_storage.py`)

Persistence layer for learned expectations.

**Key Methods**:
- `save_expectation()` - Upsert logic (insert or update)
- `get_expectation()` - Retrieve by table/column/metric
- `_insert_expectation()`, `_update_expectation()` - SQL execution
- `_expectation_to_params()`, `_row_to_expectation()` - Serialization

**Design Decisions**:
- Uses upsert pattern (check existence, then insert or update)
- Updates increment `expectation_version` for audit trail
- Stores JSON fields (distribution_params, category_distribution) as TEXT
- Handles NULL schema_name gracefully

#### 3. ResultWriter Integration (`baselinr/storage/writer.py`)

Integration point where learning is triggered after profiling.

**Integration**:
- Called after enrichment metrics are calculated
- Only executes if `config.enable_expectation_learning` is True
- Iterates through columns and numeric metrics
- Handles errors gracefully (logs warning, continues)
- Doesn't block profiling completion if learning fails

## Database Schema

### Table: `baselinr_expectations`

```sql
CREATE TABLE baselinr_expectations (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    column_name VARCHAR(255) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    column_type VARCHAR(100),
    
    -- Expected statistics
    expected_mean FLOAT,
    expected_variance FLOAT,
    expected_stddev FLOAT,
    expected_min FLOAT,
    expected_max FLOAT,
    
    -- Control limits
    lower_control_limit FLOAT,
    upper_control_limit FLOAT,
    lcl_method VARCHAR(50),      -- 'shewhart', 'ewma', etc.
    ucl_method VARCHAR(50),
    
    -- EWMA
    ewma_value FLOAT,
    ewma_lambda FLOAT DEFAULT 0.2,
    
    -- Distribution
    distribution_type VARCHAR(50),  -- 'normal', 'empirical', etc.
    distribution_params TEXT,        -- JSON of distribution parameters
    
    -- Categorical
    category_distribution TEXT,      -- JSON: {"value": frequency, ...}
    
    -- Learning metadata
    sample_size INTEGER,
    learning_window_days INTEGER,
    last_updated TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expectation_version INTEGER DEFAULT 1,
    
    UNIQUE KEY unique_expectation (table_name, schema_name, column_name, metric_name),
    INDEX idx_table_column (table_name, schema_name, column_name),
    INDEX idx_last_updated (last_updated DESC)
);
```

### Schema Design Decisions

1. **Unique Constraint**: One expectation per table/column/metric combination
2. **Version Tracking**: `expectation_version` increments on each update for audit trail
3. **JSON Storage**: Distribution params and category distributions stored as TEXT (JSON)
   - Allows flexibility for different distribution types
   - Easy to query but requires JSON parsing
4. **Indexes**: Optimized for lookup by table/column and by update time
5. **Nullable Fields**: Many fields nullable to handle partial learning (e.g., no categorical data)

## Control Limits

### Shewhart Control Limits

**Method**: 3-sigma limits (mean ± 3 × standard deviation)

**Formula**:
```
LCL = mean - (3 × stddev)
UCL = mean + (3 × stddev)
```

**When to Use**: Default method, works well for normally distributed data

**Limitations**: 
- Assumes normal distribution
- May be too wide or too narrow for skewed data
- Doesn't account for trends

### EWMA (Exponentially Weighted Moving Average)

**Method**: Smooths historical values with exponential weighting

**Formula**:
```
EWMA(t) = λ × value(t) + (1 - λ) × EWMA(t-1)
```

Where `λ` (lambda) is the smoothing parameter (default: 0.2)

**Control Limits**: Computed using asymptotic variance of EWMA statistic

**When to Use**: Better for detecting small, gradual shifts

**Current Status**: EWMA value is computed but not yet used for control limits (planned enhancement)

## Distribution Learning

### Normal Distribution Detection

**Heuristic**:
1. Calculate skewness (third moment)
2. Compare mean and median
3. If `|skewness| < 0.5` AND `|mean - median| / mean < 0.2`: classify as normal

**Distribution Parameters** (normal):
```json
{
  "mean": 42.5,
  "stddev": 3.2
}
```

### Empirical Distribution

**When**: Data doesn't fit normal distribution or insufficient data

**Distribution Parameters** (empirical):
```json
{
  "mean": 42.5,
  "stddev": 3.2,
  "min": 35.0,
  "max": 50.0,
  "skewness": 1.2
}
```

**Future Enhancements**: 
- Support for other distributions (exponential, uniform, etc.)
- Statistical tests (Shapiro-Wilk, Anderson-Darling) for normality

## Categorical Distribution Learning

### Process

1. Query historical runs for `top_values` or `category_distribution` metrics
2. Aggregate category counts across runs
3. Normalize to frequencies: `frequency(category) = count(category) / total_count`
4. Store as JSON: `{"category1": 0.45, "category2": 0.30, ...}`

### Example

```json
{
  "active": 0.65,
  "inactive": 0.25,
  "pending": 0.10
}
```

**Use Case**: Detect unexpected category values or frequency shifts

**Limitations**:
- Requires `top_values` or `category_distribution` metric to be computed during profiling
- Only learns from historical data, may miss new categories

## Integration Points

### 1. Profiling Workflow

**Location**: `baselinr/storage/writer.py::write_results()`

**Trigger**: After enrichment metrics are calculated

**Flow**:
```python
if config.enable_expectation_learning:
    self._learn_expectations(result)
```

### 2. Configuration

**Location**: `baselinr/config/schema.py::StorageConfig`

**Options**:
- `enable_expectation_learning: bool`
- `learning_window_days: int`
- `min_samples: int`
- `ewma_lambda: float`

### 3. Database Migration

**Location**: `baselinr/storage/migrations/versions/v3_expectations.py`

**Migration**: Creates `baselinr_expectations` table

**Version**: Schema version 3

**Dialect Support**: Generic SQL and Snowflake-specific DDL

## Performance Considerations

### Query Performance

**Historical Metrics Query**:
- Joins `baselinr_results` with `baselinr_runs`
- Filters by table, column, metric, date window
- Orders by timestamp
- **Optimization**: Indexes on `(dataset_name, column_name, metric_name)` and `profiled_at`

**Impact**: 
- Runs once per column/metric combination after each profiling run
- Minimal impact if profiled tables have few columns/metrics
- Scales with number of tables × columns × metrics

### Storage Impact

**Per Expectation**: ~500 bytes (with JSON fields)

**Estimation**:
- 100 tables × 10 columns × 5 metrics = 5,000 expectations
- Total storage: ~2.5 MB (negligible)

**Growth**: Linear with number of table/column/metric combinations

### Learning Time

**Per Expectation**: ~10-50ms (database query + computation)

**Total Time**: 
- 100 tables × 10 columns × 5 metrics = 5,000 expectations
- Total time: ~50-250 seconds (can run in parallel, not currently implemented)

**Recommendation**: Learning runs after profiling, doesn't block user-facing operations

## Error Handling

### Graceful Degradation

1. **Insufficient Samples**: Logs debug, returns None, continues
2. **Query Errors**: Logs warning, skips that metric, continues
3. **Computation Errors**: Logs warning, skips that metric, continues
4. **Storage Errors**: Logs warning, continues with other metrics

**Design Principle**: Learning failures should never break profiling or drift detection

### Logging

- **Debug**: Insufficient samples, skipped learning
- **Warning**: Errors during learning (query, computation, storage)
- **Info**: Not used (to avoid noise)

## Future Enhancements

1. **EWMA Control Limits**: Use EWMA for control limits instead of just Shewhart
2. **Distribution Tests**: Add statistical tests for normality (Shapiro-Wilk, etc.)
3. **Parallel Learning**: Learn expectations in parallel for multiple metrics
4. **Incremental Updates**: Update expectations incrementally instead of full recomputation
5. **Outlier Detection**: Automatic outlier detection using learned expectations
6. **Adaptive Windows**: Automatically adjust window size based on data frequency
7. **Multiple Distribution Types**: Support exponential, uniform, log-normal, etc.
8. **Time-Series Aware**: Account for trends, seasonality in expectations
9. **Per-Table Configuration**: Allow different learning parameters per table

## Testing Strategy

### Unit Tests

- `ExpectationLearner`:
  - Test statistics computation with known values
  - Test control limits calculation
  - Test distribution detection heuristics
  - Test insufficient samples handling

- `ExpectationStorage`:
  - Test insert/update/retrieve operations
  - Test serialization/deserialization
  - Test NULL handling

### Integration Tests

- End-to-end: Profile → Learn → Store → Retrieve
- Multiple runs: Ensure expectations update correctly
- Error scenarios: Test graceful degradation

### Migration Tests

- Verify v3 migration creates table correctly
- Test both generic SQL and Snowflake dialects

## Related Documentation

- [User Guide: Expectation Learning](../guides/EXPECTATION_LEARNING.md) - User-facing documentation
- [Drift Detection Architecture](DRIFT_DETECTION.md) - Related baseline system
- [Storage Schema](../schemas/SCHEMA_REFERENCE.md) - Database schema reference


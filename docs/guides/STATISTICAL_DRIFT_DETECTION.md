# Statistical Drift Detection

Baselinr provides advanced statistical drift detection using multiple statistical tests that can be selected and combined based on column type and metric characteristics.

## Overview

The statistical drift detection strategy uses rigorous statistical methods to detect changes in data distributions, not just simple threshold-based comparisons. It automatically selects appropriate tests based on whether your data is numeric or categorical.

## When to Use Statistical Tests

Statistical tests are ideal when you need:

- **Distribution-aware detection**: Detect changes in data shape, not just mean shifts
- **Categorical data analysis**: Track changes in category distributions
- **Reduced false positives**: Statistical significance testing reduces noise
- **Multiple perspectives**: Combine multiple tests for comprehensive coverage
- **Histogram data**: Leverage histogram information when available

## Configuration

### Basic Configuration

```yaml
drift_detection:
  strategy: statistical
  statistical:
    tests:
      - ks_test
      - psi
      - chi_square
    sensitivity: medium
```

### Full Configuration with Test Parameters

```yaml
drift_detection:
  strategy: statistical
  statistical:
    tests:
      - ks_test          # Kolmogorov-Smirnov test
      - psi              # Population Stability Index
      - z_score          # Z-score test
      - chi_square       # Chi-square test
      - entropy          # Entropy change
      - top_k            # Top-K stability
    sensitivity: medium  # low, medium, or high
    test_params:
      ks_test:
        alpha: 0.05      # Significance level
      psi:
        buckets: 10      # Number of distribution buckets
        threshold: 0.2   # PSI threshold for drift
      z_score:
        z_threshold: 2.0 # Z-score threshold (std devs)
      chi_square:
        alpha: 0.05      # Significance level
      entropy:
        entropy_threshold: 0.1  # Entropy change threshold
      top_k:
        k: 10                    # Number of top categories
        similarity_threshold: 0.7  # Similarity threshold
```

## Available Statistical Tests

### Numeric Column Tests

#### 1. Kolmogorov-Smirnov (KS) Test

**Test Name**: `ks_test`

**Description**: Compares the distribution of baseline vs current data. Good for detecting shape changes (skew, multimodality, heavy tails).

**Parameters**:
- `alpha`: Significance level (default: 0.05)

**How it works**:
- Compares empirical cumulative distribution functions (CDFs)
- Returns KS statistic (maximum difference between CDFs)
- Calculates p-value for statistical significance
- Works best with histogram data, but can approximate from summary statistics

**Example**:
```yaml
test_params:
  ks_test:
    alpha: 0.05
```

**Best for**: Detecting distribution shape changes in numeric columns

---

#### 2. Population Stability Index (PSI)

**Test Name**: `psi`

**Description**: Bucket-based drift detection. Good for monitoring slow drifts over long periods.

**Parameters**:
- `buckets`: Number of buckets for distribution (default: 10)
- `threshold`: PSI threshold for drift detection (default: 0.2)

**PSI Score Interpretation**:
- `< 0.1`: No significant drift
- `0.1-0.2`: Minor drift
- `0.2-0.5`: Moderate drift
- `> 0.5`: Significant drift

**Example**:
```yaml
test_params:
  psi:
    buckets: 20
    threshold: 0.15
```

**Best for**: Long-term drift monitoring, especially with histogram data

---

#### 3. Z-Score / Variance Test

**Test Name**: `z_score`

**Description**: Detects shifts in mean/variance using standard deviation.

**Parameters**:
- `z_threshold`: Z-score threshold in standard deviations (default: 2.0)

**How it works**:
- Calculates: `z = |(current_mean - baseline_mean) / baseline_stddev|`
- Flags drift if z-score exceeds threshold
- Severity based on z-score magnitude

**Example**:
```yaml
test_params:
  z_score:
    z_threshold: 2.5  # More sensitive (2.5 std devs)
```

**Best for**: Detecting mean shifts when you have stddev information

---

### Categorical Column Tests

#### 4. Chi-Square Test

**Test Name**: `chi_square`

**Description**: Tests whether the distribution of categories has changed significantly.

**Parameters**:
- `alpha`: Significance level (default: 0.05)

**How it works**:
- Compares observed vs expected category frequencies
- Calculates chi-square statistic
- Uses p-value for statistical significance

**Example**:
```yaml
test_params:
  chi_square:
    alpha: 0.01  # More strict (1% significance)
```

**Best for**: Detecting changes in category distributions

---

#### 5. Entropy Change Test

**Test Name**: `entropy`

**Description**: Detects changes in Shannon entropy (randomness/uniformity) of category distributions.

**Parameters**:
- `entropy_threshold`: Threshold for entropy change (default: 0.1)

**How it works**:
- Calculates Shannon entropy: `H = -Σ(p * log2(p))`
- Compares baseline vs current entropy
- Flags drift if entropy change exceeds threshold

**Example**:
```yaml
test_params:
  entropy:
    entropy_threshold: 0.15
```

**Best for**: Detecting changes in data uniformity/randomness

---

#### 6. Top-K Stability Test

**Test Name**: `top_k`

**Description**: Tracks the top-K most frequent categories and detects changes.

**Parameters**:
- `k`: Number of top categories to track (default: 10)
- `similarity_threshold`: Similarity threshold for stability (default: 0.7)

**How it works**:
- Extracts top-K categories from baseline and current
- Calculates Jaccard similarity (intersection / union)
- Flags drift if similarity drops below threshold

**Example**:
```yaml
test_params:
  top_k:
    k: 20
    similarity_threshold: 0.8  # More strict
```

**Best for**: Monitoring stability of most common categories

---

## Sensitivity Levels

The `sensitivity` parameter adjusts thresholds across all tests:

- **`low`**: Less sensitive (higher thresholds) - reduces false positives
- **`medium`**: Balanced (default thresholds) - recommended starting point
- **`high`**: More sensitive (lower thresholds) - catches more drift, may have more false positives

**How it works**:
- Low sensitivity: thresholds × 1.5
- Medium sensitivity: thresholds × 1.0 (default)
- High sensitivity: thresholds × 0.5

## Test Selection

The statistical strategy automatically selects applicable tests based on:

1. **Column Type**: Numeric tests for numeric columns, categorical tests for categorical columns
2. **Metric Type**: Tests check if they support the specific metric being compared
3. **Data Availability**: Tests that can't run (insufficient data) are skipped gracefully

### Automatic Test Selection

```python
# Numeric column with mean metric
# → Runs: ks_test, psi, z_score (if data available)

# Categorical column with distinct_count metric
# → Runs: chi_square, entropy, top_k (if data available)
```

## Data Requirements

### Optimal Data

Statistical tests work best with:

- **Histogram data**: For KS test and PSI (enables distribution comparison)
- **Category distributions**: For categorical tests (top values, frequencies)
- **Summary statistics**: Mean, stddev, min, max (for approximations)

### Fallback Behavior

If optimal data isn't available:

- Tests use approximations from summary statistics
- Some tests may skip with a warning
- System falls back to threshold-based detection if no tests can run

### Enabling Histogram Data

To get the best results from statistical tests, enable histograms in your profiling config:

```yaml
profiling:
  compute_histograms: true
  histogram_bins: 10  # More bins = more granular distribution
```

## Usage Examples

### Example 1: Numeric Columns with Histograms

```yaml
drift_detection:
  strategy: statistical
  statistical:
    tests:
      - ks_test
      - psi
      - z_score
    sensitivity: medium
    test_params:
      ks_test:
        alpha: 0.05
      psi:
        buckets: 15
        threshold: 0.2
```

**What it detects**:
- Distribution shape changes (KS test)
- Bucket-level shifts (PSI)
- Mean shifts (Z-score)

### Example 2: Categorical Columns

```yaml
drift_detection:
  strategy: statistical
  statistical:
    tests:
      - chi_square
      - entropy
      - top_k
    sensitivity: high
    test_params:
      chi_square:
        alpha: 0.01
      top_k:
        k: 15
        similarity_threshold: 0.8
```

**What it detects**:
- Category distribution changes (Chi-square)
- Entropy/uniformity changes (Entropy)
- Top category stability (Top-K)

### Example 3: Comprehensive Coverage

```yaml
drift_detection:
  strategy: statistical
  statistical:
    tests:
      - ks_test
      - psi
      - z_score
      - chi_square
      - entropy
      - top_k
    sensitivity: medium
```

**What it detects**: All types of drift for both numeric and categorical columns

## Understanding Results

### Test Result Aggregation

When multiple tests run, results are aggregated:

- **Drift Detection**: Any test detecting drift → overall drift detected
- **Severity**: Maximum severity across all tests
- **Score**: Average score across all tests
- **Metadata**: Detailed results from each test included

### Example Output

```python
report = detector.detect_drift("customers")

for drift in report.column_drifts:
    if drift.drift_detected:
        print(f"{drift.column_name}.{drift.metric_name}")
        print(f"  Severity: {drift.drift_severity}")
        print(f"  Tests run: {drift.metadata['test_results']}")
        
        # Individual test results
        for test_result in drift.metadata['test_results']:
            print(f"    {test_result['test']}: score={test_result['score']}, "
                  f"p_value={test_result['p_value']}, "
                  f"drift={test_result['drift_detected']}")
```

### Metadata Structure

```python
drift.metadata = {
    'strategy': 'statistical',
    'tests_run': ['ks_test', 'psi', 'z_score'],
    'test_results': [
        {
            'test': 'ks_test',
            'score': 0.25,
            'p_value': 0.001,
            'drift_detected': True,
            'severity': 'high',
            'metadata': {
                'alpha': 0.05,
                'statistic': 0.25,
                'p_value': 0.001
            }
        },
        # ... more test results
    ],
    'aggregated_score': 0.18,
    'sensitivity': 'medium'
}
```

## Best Practices

### 1. Start with Default Configuration

```yaml
drift_detection:
  strategy: statistical
  statistical:
    tests:
      - ks_test
      - psi
      - chi_square
    sensitivity: medium
```

### 2. Enable Histograms

For best results with KS test and PSI:

```yaml
profiling:
  compute_histograms: true
  histogram_bins: 10
```

### 3. Adjust Sensitivity Based on Your Needs

```yaml
# Production: Lower sensitivity (fewer false positives)
sensitivity: low

# Development: Higher sensitivity (catch more issues)
sensitivity: high
```

### 4. Select Tests Based on Your Data

```yaml
# Numeric-heavy dataset
tests:
  - ks_test
  - psi
  - z_score

# Categorical-heavy dataset
tests:
  - chi_square
  - entropy
  - top_k

# Mixed dataset
tests:
  - ks_test
  - psi
  - chi_square
  - top_k
```

### 5. Tune Test-Specific Parameters

```yaml
test_params:
  # More strict KS test
  ks_test:
    alpha: 0.01
  
  # More buckets for finer PSI analysis
  psi:
    buckets: 20
    threshold: 0.15
  
  # Track more top categories
  top_k:
    k: 20
    similarity_threshold: 0.8
```

## Performance Considerations

- **Multiple tests**: Running more tests takes slightly longer, but tests run in parallel where possible
- **Histogram data**: Requires more storage but enables better detection
- **Large datasets**: Statistical tests are efficient and scale well

## Troubleshooting

### "No statistical tests could run"

**Problem**: Tests don't support the column type or metric, or insufficient data.

**Solutions**:
1. Check column type is numeric or categorical
2. Enable histograms: `compute_histograms: true`
3. Ensure you have summary statistics (mean, stddev, etc.)
4. System will fallback to threshold-based detection

### "All tests fail"

**Problem**: Data format issues or missing dependencies.

**Solutions**:
1. Check data is in expected format (histograms, distributions)
2. Install scipy for better test accuracy: `pip install scipy`
3. Check logs for specific error messages

### "Too many false positives"

**Problem**: Sensitivity too high or thresholds too low.

**Solutions**:
1. Lower sensitivity: `sensitivity: low`
2. Increase test thresholds in `test_params`
3. Remove more sensitive tests (e.g., remove `entropy` if too noisy)

### "Not detecting obvious drift"

**Problem**: Sensitivity too low or thresholds too high.

**Solutions**:
1. Increase sensitivity: `sensitivity: high`
2. Lower test thresholds in `test_params`
3. Add more tests to the list

## Comparison with Other Strategies

| Feature | Absolute Threshold | Standard Deviation | Statistical Tests |
|---------|-------------------|-------------------|-------------------|
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Statistical Rigor** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Distribution Awareness** | ❌ | ❌ | ✅ |
| **Categorical Support** | ❌ | ❌ | ✅ |
| **Data Requirements** | Minimal | Summary stats | Histograms preferred |
| **False Positives** | Medium | Low | Very Low |
| **Setup Complexity** | Low | Medium | Medium |

## See Also

- [Drift Detection Guide](DRIFT_DETECTION.md) - General drift detection documentation
- [Configuration Examples](../examples/config.yml) - Example configurations
- [Profiling Metrics](../README.md#profiling-metrics) - Available metrics


# Drift Detection in ProfileMesh

ProfileMesh provides a flexible, configurable drift detection system to identify changes in your data over time.

## Overview

Drift detection compares profiling results from different runs to identify:
- **Schema changes**: Added or removed columns
- **Statistical changes**: Changes in metrics like mean, count, null percentage, etc.
- **Severity classification**: Low, medium, or high severity based on the magnitude of change

## Configuration

Drift detection behavior is controlled through the `drift_detection` section of your configuration file.

### Basic Configuration

```yaml
drift_detection:
  strategy: absolute_threshold
  
  absolute_threshold:
    low_threshold: 5.0      # 5% change
    medium_threshold: 15.0   # 15% change
    high_threshold: 30.0     # 30% change
```

## Available Strategies

### 1. Absolute Threshold Strategy (Default)

**Name**: `absolute_threshold`

**Description**: Classifies drift based on absolute percentage change from baseline.

**Parameters**:
- `low_threshold`: Percentage change that triggers low severity (default: 5.0%)
- `medium_threshold`: Percentage change that triggers medium severity (default: 15.0%)
- `high_threshold`: Percentage change that triggers high severity (default: 30.0%)

**Example Configuration**:
```yaml
drift_detection:
  strategy: absolute_threshold
  absolute_threshold:
    low_threshold: 10.0
    medium_threshold: 20.0
    high_threshold: 40.0
```

**How it works**:
1. Calculates percentage change: `(current - baseline) / baseline * 100`
2. Takes absolute value of percentage change
3. Compares against thresholds to determine severity

**Best for**:
- Simple drift detection
- Well-understood data with stable distributions
- Quick setup without historical data

**Example**:
- Baseline count: 1000
- Current count: 1200
- Change: +20%
- Result: **Medium severity** (exceeds 15% threshold)

---

### 2. Standard Deviation Strategy

**Name**: `standard_deviation`

**Description**: Classifies drift based on number of standard deviations from baseline.

**Parameters**:
- `low_threshold`: Number of std devs for low severity (default: 1.0)
- `medium_threshold`: Number of std devs for medium severity (default: 2.0)
- `high_threshold`: Number of std devs for high severity (default: 3.0)

**Example Configuration**:
```yaml
drift_detection:
  strategy: standard_deviation
  standard_deviation:
    low_threshold: 1.5
    medium_threshold: 2.5
    high_threshold: 3.5
```

**How it works**:
1. Calculates how many standard deviations the current value is from the mean
2. Compares against threshold (in number of std devs)
3. Classifies severity based on statistical significance

**Best for**:
- Data with known statistical properties
- When you want statistical significance
- Reducing false positives from normal variation

**Note**: Current implementation uses a simplified approximation. For production use with historical data, this would calculate actual mean and standard deviation from past runs.

---

### 3. ML-Based Strategy (Placeholder)

**Name**: `ml_based`

**Description**: Placeholder for machine learning-based drift detection.

**Status**: ⚠️ **Not Yet Implemented**

**Planned Features**:
- Anomaly detection using Isolation Forest
- Time-series drift detection with LSTM
- Distribution shift detection (KS test, Chi-squared)
- Autoencoder-based detection
- Custom model support

**Example Configuration** (future):
```yaml
drift_detection:
  strategy: ml_based
  ml_based:
    model_type: isolation_forest
    sensitivity: 0.8
    min_samples: 100
    contamination: 0.1
```

**Extensibility**: See "Custom Strategies" section below.

---

## Usage Examples

### CLI Usage

```bash
# Basic drift detection (uses config)
profilemesh drift --config config.yml --dataset customers

# Specify specific runs to compare
profilemesh drift --config config.yml \
  --dataset customers \
  --baseline <run-id-1> \
  --current <run-id-2>

# Fail on critical drift (for CI/CD)
profilemesh drift --config config.yml \
  --dataset customers \
  --fail-on-drift
```

### Python API Usage

```python
from profilemesh.config.loader import ConfigLoader
from profilemesh.drift.detector import DriftDetector

# Load config
config = ConfigLoader.load_from_file("config.yml")

# Create detector with config
detector = DriftDetector(config.storage, config.drift_detection)

# Detect drift
report = detector.detect_drift(
    dataset_name="customers",
    baseline_run_id=None,  # Uses second-latest
    current_run_id=None     # Uses latest
)

# Check results
print(f"Total drifts: {report.summary['total_drifts']}")
print(f"High severity: {report.summary['drift_by_severity']['high']}")

for drift in report.column_drifts:
    if drift.drift_detected:
        print(f"{drift.column_name}.{drift.metric_name}: {drift.drift_severity}")
```

### Using Different Strategies

```python
from profilemesh.drift.detector import DriftDetector
from profilemesh.config.schema import DriftDetectionConfig, StorageConfig

# Configure standard deviation strategy
drift_config = DriftDetectionConfig(
    strategy="standard_deviation",
    standard_deviation={
        "low_threshold": 1.5,
        "medium_threshold": 2.5,
        "high_threshold": 3.5
    }
)

# Create detector
detector = DriftDetector(storage_config, drift_config)

# Use it
report = detector.detect_drift("customers")
```

---

## Custom Drift Detection Strategies

You can create custom drift detection strategies by extending the `DriftDetectionStrategy` base class.

### Step 1: Create Your Strategy

```python
from profilemesh.drift.strategies import DriftDetectionStrategy, DriftResult
from typing import Any, Optional

class MyCustomStrategy(DriftDetectionStrategy):
    """My custom drift detection logic."""
    
    def __init__(self, custom_param: float = 1.0):
        """Initialize with custom parameters."""
        self.custom_param = custom_param
    
    def calculate_drift(
        self,
        baseline_value: Any,
        current_value: Any,
        metric_name: str,
        column_name: str
    ) -> Optional[DriftResult]:
        """Implement your drift calculation logic."""
        
        # Your custom logic here
        if baseline_value is None or current_value is None:
            return None
        
        # Example: custom scoring logic
        score = abs(current_value - baseline_value) / self.custom_param
        
        # Classify severity
        if score >= 3.0:
            severity = "high"
            detected = True
        elif score >= 2.0:
            severity = "medium"
            detected = True
        elif score >= 1.0:
            severity = "low"
            detected = True
        else:
            severity = "none"
            detected = False
        
        return DriftResult(
            drift_detected=detected,
            drift_severity=severity,
            score=score,
            change_absolute=current_value - baseline_value,
            metadata={'method': 'custom', 'param': self.custom_param}
        )
    
    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "my_custom_strategy"
```

### Step 2: Register Your Strategy

```python
from profilemesh.drift.strategies import DRIFT_STRATEGIES

# Register your strategy
DRIFT_STRATEGIES['my_custom_strategy'] = MyCustomStrategy
```

### Step 3: Use in Configuration

```yaml
drift_detection:
  strategy: my_custom_strategy
  my_custom_strategy:
    custom_param: 2.5
```

---

## Understanding Drift Reports

### Drift Report Structure

```python
report = detector.detect_drift("customers")

# Attributes:
report.dataset_name              # "customers"
report.baseline_run_id           # UUID of baseline run
report.current_run_id            # UUID of current run
report.baseline_timestamp        # Datetime of baseline
report.current_timestamp         # Datetime of current
report.column_drifts             # List of ColumnDrift objects
report.schema_changes            # List of schema change strings
report.summary                   # Summary statistics
```

### Column Drift Object

```python
for drift in report.column_drifts:
    drift.column_name           # "age"
    drift.metric_name           # "mean"
    drift.baseline_value        # 35.5
    drift.current_value         # 42.3
    drift.change_absolute       # 6.8
    drift.change_percent        # 19.15%
    drift.drift_detected        # True
    drift.drift_severity        # "medium"
```

### Summary Statistics

```python
summary = report.summary

summary['total_drifts']                    # 5
summary['schema_changes']                   # 1
summary['drift_by_severity']['high']       # 2
summary['drift_by_severity']['medium']     # 2
summary['drift_by_severity']['low']        # 1
summary['has_critical_drift']              # True
```

---

## Best Practices

### 1. Choose the Right Strategy

- **Absolute Threshold**: Start here for simplicity
- **Standard Deviation**: Use when you have statistical knowledge of your data
- **ML-Based**: For complex patterns and anomaly detection (when implemented)

### 2. Tune Your Thresholds

Start conservative and adjust based on your data:

```yaml
# Conservative (catch more drift)
absolute_threshold:
  low_threshold: 3.0
  medium_threshold: 10.0
  high_threshold: 20.0

# Moderate (balanced)
absolute_threshold:
  low_threshold: 5.0
  medium_threshold: 15.0
  high_threshold: 30.0

# Permissive (reduce noise)
absolute_threshold:
  low_threshold: 10.0
  medium_threshold: 25.0
  high_threshold: 50.0
```

### 3. Different Strategies for Different Environments

```yaml
# config_prod.yml - strict thresholds
drift_detection:
  strategy: absolute_threshold
  absolute_threshold:
    low_threshold: 3.0
    medium_threshold: 10.0
    high_threshold: 20.0

# config_dev.yml - permissive thresholds
drift_detection:
  strategy: absolute_threshold
  absolute_threshold:
    low_threshold: 15.0
    medium_threshold: 30.0
    high_threshold: 50.0
```

### 4. Monitor Drift Over Time

```python
# Profile regularly (e.g., daily)
engine.profile()

# Check drift trends
recent_reports = []
for i in range(7):  # Last 7 days
    report = detector.detect_drift("customers")
    recent_reports.append(report)

# Analyze trend
drift_counts = [r.summary['total_drifts'] for r in recent_reports]
print(f"Drift trend: {drift_counts}")
```

### 5. Integrate with Alerts

```python
report = detector.detect_drift("customers")

if report.summary['has_critical_drift']:
    # Send alert
    send_slack_alert(f"Critical drift detected in customers table!")
    
    # Email details
    send_email(
        subject="Data Drift Alert",
        body=format_drift_report(report)
    )
```

---

## Roadmap

Future enhancements planned:

- [ ] **Historical baseline**: Use rolling window of past runs instead of single baseline
- [ ] **Column-specific thresholds**: Different thresholds per column or metric
- [ ] **ML-based detection**: Implement actual ML strategies
- [ ] **Statistical tests**: KS test, Chi-squared for distribution shifts
- [ ] **Drift trends**: Track drift over time, not just point-in-time
- [ ] **Auto-tuning**: Automatically suggest thresholds based on historical data
- [ ] **Drift explanations**: AI-powered explanations of why drift occurred

---

## Troubleshooting

### "Not enough runs for drift detection"

**Problem**: You need at least 2 profiling runs.

**Solution**: Run profiling twice:
```bash
profilemesh profile --config config.yml
# ... wait or make changes ...
profilemesh profile --config config.yml
profilemesh drift --config config.yml --dataset customers
```

### "All drifts are high severity"

**Problem**: Thresholds are too strict for your data.

**Solution**: Increase thresholds:
```yaml
drift_detection:
  absolute_threshold:
    low_threshold: 10.0
    medium_threshold: 25.0
    high_threshold: 50.0
```

### "No drift detected but data changed significantly"

**Problem**: Thresholds are too permissive.

**Solution**: Lower thresholds or switch strategies:
```yaml
drift_detection:
  strategy: standard_deviation  # More sensitive
  standard_deviation:
    low_threshold: 1.0
    medium_threshold: 1.5
    high_threshold: 2.0
```

---

## See Also

- [README.md](README.md) - Main documentation
- [DEVELOPMENT.md](DEVELOPMENT.md) - Adding custom strategies
- [examples/config.yml](examples/config.yml) - Example configurations


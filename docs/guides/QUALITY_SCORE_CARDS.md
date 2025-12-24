# Quality Score Cards Guide

## Overview

Quality Score Cards provide a unified, easy-to-understand view of data quality across tables, columns, and the entire system. Each score card combines multiple quality dimensions into a single actionable score (0-100) that helps you quickly identify and prioritize data quality issues.

## Understanding Scores

### Overall Score

The overall quality score is a weighted combination of six quality dimensions:

1. **Completeness** (25%): Based on null ratios across columns
2. **Validity** (25%): Based on validation rule pass rates
3. **Consistency** (20%): Based on drift detection and schema stability
4. **Freshness** (15%): Based on data recency and update frequency
5. **Uniqueness** (10%): Based on duplicate detection and unique constraints
6. **Accuracy** (5%): Based on anomaly detection and statistical outliers

### Score Levels

- **Table-level**: Score for individual tables
- **Column-level**: Score for individual columns (optional)
- **Schema-level**: Aggregated score for all tables in a schema
- **System-level**: Overall score across all monitored tables

### Score Status

Scores are classified into three status levels:

- **Healthy** (≥80): Data quality is good, no immediate action needed
- **Warning** (60-79): Data quality issues detected, review recommended
- **Critical** (&lt;60): Significant data quality problems, immediate attention required

## Configuration

### Component Weights

You can customize the weights assigned to each quality dimension. Weights must sum to 100%.

**Default weights:**
- Completeness: 25%
- Validity: 25%
- Consistency: 20%
- Freshness: 15%
- Uniqueness: 10%
- Accuracy: 5%

**Example configuration:**
```yaml
quality_scoring:
  enabled: true
  weights:
    completeness: 30
    validity: 30
    consistency: 20
    freshness: 10
    uniqueness: 5
    accuracy: 5
```

### Thresholds

Configure the score thresholds for status classification:

```yaml
quality_scoring:
  thresholds:
    healthy: 80    # Scores >= 80 are healthy
    warning: 60    # Scores >= 60 are warnings
    critical: 0    # Scores < 60 are critical
```

### Freshness Settings

Configure freshness thresholds in hours:

```yaml
quality_scoring:
  freshness:
    excellent: 24      # ≤ 24 hours = 100 points
    good: 48          # ≤ 48 hours = 80 points
    acceptable: 168   # ≤ 1 week = 60 points
```

### History Settings

Enable historical tracking of scores:

```yaml
quality_scoring:
  store_history: true
  history_retention_days: 90  # Keep 90 days of history
```

## CLI Usage

### Basic Score Calculation

Calculate a quality score for a specific table:

```bash
baselinr score --config config.yaml --table customers
```

### Output Formats

**Table format (default):**
```bash
baselinr score --config config.yaml --table customers --format table
```

**JSON format:**
```bash
baselinr score --config config.yaml --table customers --format json
```

### Export Scores

**Export single score to CSV:**
```bash
baselinr score --config config.yaml --table customers --export csv --output scores.csv
```

**Export single score to JSON:**
```bash
baselinr score --config config.yaml --table customers --export json --output score.json
```

**Export score history:**
```bash
baselinr score --config config.yaml --table customers --history --export csv --output history.csv
```

### Schema Filtering

Calculate scores for tables in a specific schema:

```bash
baselinr score --config config.yaml --table customers --schema public
```

## API Usage

### Get Table Score

```bash
GET /api/quality/scores/customers
```

**Response:**
```json
{
  "table_name": "customers",
  "schema_name": "public",
  "overall_score": 85.5,
  "status": "healthy",
  "trend": "improving",
  "trend_percentage": 2.3,
  "components": {
    "completeness": 90.0,
    "validity": 88.0,
    "consistency": 82.0,
    "freshness": 95.0,
    "uniqueness": 85.0,
    "accuracy": 78.0
  },
  "issues": {
    "total": 3,
    "critical": 1,
    "warnings": 2
  },
  "calculated_at": "2024-01-15T10:30:00Z"
}
```

### Get Score History

```bash
GET /api/quality/scores/customers/history?days=30
```

### Get Schema-Level Scores

```bash
GET /api/quality/scores/schema/public
```

### Get System-Level Score

```bash
GET /api/quality/scores/system
```

## Alerting

Quality score alerts are automatically emitted when:

1. **Score Degradation**: Score drops by more than 5 points
2. **Threshold Breach**: Score crosses warning or critical thresholds

### Alert Configuration

Alerts are integrated with Baselinr's event system. Configure alert hooks in your configuration:

```yaml
hooks:
  enabled: true
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#data-alerts"
      min_severity: medium
      alert_on_drift: true
      alert_on_schema_change: true
```

### Alert Events

**QualityScoreDegraded**: Emitted when score drops significantly
- `table`: Table name
- `current_score`: Current score
- `previous_score`: Previous score
- `score_change`: Change in score
- `threshold_type`: 'warning' or 'critical'

**QualityScoreThresholdBreached**: Emitted when score crosses a threshold
- `table`: Table name
- `current_score`: Current score
- `threshold_type`: 'warning' or 'critical'
- `threshold_value`: Threshold value that was breached

## Exporting Scores

### CSV Export Format

CSV exports include the following columns:
- `table_name`
- `schema_name`
- `overall_score`
- `completeness_score`
- `validity_score`
- `consistency_score`
- `freshness_score`
- `uniqueness_score`
- `accuracy_score`
- `status`
- `total_issues`
- `critical_issues`
- `warnings`
- `calculated_at`
- `period_start`
- `period_end`

### JSON Export Format

JSON exports include full score objects with all metadata:

```json
[
  {
    "overall_score": 85.5,
    "completeness_score": 90.0,
    "validity_score": 88.0,
    "consistency_score": 82.0,
    "freshness_score": 95.0,
    "uniqueness_score": 85.0,
    "accuracy_score": 78.0,
    "status": "healthy",
    "total_issues": 3,
    "critical_issues": 1,
    "warnings": 2,
    "table_name": "customers",
    "schema_name": "public",
    "calculated_at": "2024-01-15T10:30:00Z",
    "period_start": "2024-01-08T10:30:00Z",
    "period_end": "2024-01-15T10:30:00Z"
  }
]
```

## Best Practices

### 1. Regular Monitoring

Calculate scores regularly as part of your data pipeline:

```bash
# Add to your cron job or workflow
baselinr score --config config.yaml --table customers
```

### 2. Set Appropriate Thresholds

Adjust thresholds based on your data quality requirements:

- **Strict environments**: Set healthy threshold to 90
- **Development environments**: Set healthy threshold to 70

### 3. Monitor Trends

Track score trends over time to identify gradual degradation:

```bash
baselinr score --config config.yaml --table customers --history --export json --output trends.json
```

### 4. Configure Alerts

Set up alert hooks to be notified of score degradation:

```yaml
hooks:
  enabled: true
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#data-quality"
```

### 5. Customize Weights

Adjust component weights based on your priorities:

- **Data completeness critical**: Increase completeness weight
- **Validation important**: Increase validity weight
- **Freshness matters**: Increase freshness weight

## Troubleshooting

### Score Not Calculating

**Problem**: Score command returns no results or errors

**Solutions**:
1. Verify quality scoring is enabled in config:
   ```yaml
   quality_scoring:
     enabled: true
   ```

2. Check that required tables exist:
   - `baselinr_results` (profiling results)
   - `baselinr_validation_results` (validation results)
   - `baselinr_events` (drift/anomaly events)

3. Verify table has been profiled:
   ```bash
   baselinr query runs --table customers
   ```

### Scores Seem Incorrect

**Problem**: Scores don't match expectations

**Solutions**:
1. Check component scores individually:
   ```bash
   baselinr score --table customers --format json
   ```

2. Verify data exists for all components:
   - Profiling results for completeness/uniqueness
   - Validation results for validity
   - Events for consistency/accuracy

3. Check freshness calculation:
   - Verify `baselinr_runs` table has recent entries
   - Check `profiled_at` timestamps

### Export Fails

**Problem**: Export command fails or produces empty files

**Solutions**:
1. Verify output path is writable
2. Check file permissions
3. Ensure table has scores:
   ```bash
   baselinr score --table customers
   ```

### Alerts Not Firing

**Problem**: Score degradation doesn't trigger alerts

**Solutions**:
1. Verify hooks are enabled:
   ```yaml
   hooks:
     enabled: true
   ```

2. Check event bus is initialized in score command
3. Verify alert thresholds are configured correctly
4. Check hook logs for errors

## Related Documentation

- [Data Validation Guide](DATA_VALIDATION.md)
- [Drift Detection Guide](DRIFT_DETECTION.md)
- [Anomaly Detection Guide](ANOMALY_DETECTION.md)
- [Event & Alert Hooks](../architecture/EVENTS_AND_HOOKS.md)
- [Configuration Reference](../../website/docs/reference/CONFIG_REFERENCE.md)

## Examples

### Example 1: Daily Score Check

```bash
#!/bin/bash
# Daily quality score check

TABLES=("customers" "orders" "products")

for table in "${TABLES[@]}"; do
  baselinr score --config config.yaml --table "$table" --export csv --output "scores_${table}_$(date +%Y%m%d).csv"
done
```

### Example 2: Score Monitoring Script

```python
import subprocess
import json

def check_quality_scores(tables):
    results = {}
    for table in tables:
        result = subprocess.run(
            ["baselinr", "score", "--config", "config.yaml", 
             "--table", table, "--format", "json"],
            capture_output=True,
            text=True
        )
        score = json.loads(result.stdout)
        results[table] = score
        
        if score["status"] == "critical":
            print(f"ALERT: {table} has critical quality score: {score['overall_score']}")
    
    return results
```

### Example 3: Trend Analysis

```bash
# Export 90 days of history
baselinr score --config config.yaml --table customers --history --export json --output history.json

# Analyze trends (using jq)
cat history.json | jq '.[] | {date: .calculated_at, score: .overall_score}'
```







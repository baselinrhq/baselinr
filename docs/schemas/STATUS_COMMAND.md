# Baselinr Status Command

Quick reference for the `baselinr status` command - your dashboard view of profiling runs and drift detection.

## Overview

The `status` command provides a comprehensive, color-coded overview of recent profiling runs and active drift detection. Think of it as the "kubectl get pods" of data profiling - a quick way to understand your system's health at a glance.

**When to use:**
- Quick health check of your profiling system
- Monitor recent profiling activity
- Identify tables with active drift
- Continuous monitoring (with `--watch` mode)

## Basic Usage

```bash
# Show status for recent runs and drift
baselinr status --config config.yml

# Show only drift summary
baselinr status --config config.yml --drift-only

# Limit number of runs shown
baselinr status --config config.yml --limit 10

# JSON output for scripting
baselinr status --config config.yml --json

# Watch mode (auto-refresh every 5 seconds)
baselinr status --config config.yml --watch

# Watch mode with custom interval
baselinr status --config config.yml --watch 10
```

## Command Reference

### Required Arguments

- `--config, -c`: Path to configuration file (YAML or JSON)

### Optional Arguments

- `--drift-only`: Show only drift summary, skip recent runs section
- `--limit N`: Limit number of runs shown (default: 20)
- `--json`: Output machine-readable JSON instead of formatted tables
- `--watch [SECONDS]`: Auto-refresh every N seconds (default: 5). Press Ctrl+C to exit.

## Examples

### Basic Status Check

```bash
baselinr status --config config.yml
```

Shows:
- Recent profiling runs (last 24 hours, up to 20 runs)
- Active drift summary (drift events in last 7 days)

### Show Only Drift

```bash
baselinr status --config config.yml --drift-only
```

Useful when you only care about drift detection and don't need run details.

### Limit Runs Displayed

```bash
baselinr status --config config.yml --limit 5
```

Show only the 5 most recent runs.

### JSON Output

```bash
baselinr status --config config.yml --json
```

Output format:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "runs": [
    {
      "run_id": "abc-123",
      "table_name": "customers",
      "schema_name": "public",
      "profiled_at": "2024-01-15T10:00:00Z",
      "duration": "45.2s",
      "rows_scanned": 1000000,
      "metrics_count": 15,
      "anomalies_count": 0,
      "status_indicator": "🟢"
    }
  ],
  "drift_summary": [
    {
      "table_name": "orders",
      "severity": "high",
      "drift_type": "volume",
      "started_at": "2024-01-14T08:00:00Z",
      "event_count": 3
    }
  ]
}
```

### Watch Mode

```bash
baselinr status --config config.yml --watch
```

Continuously refreshes the status display every 5 seconds. Useful for monitoring during active profiling or debugging.

Custom refresh interval:
```bash
baselinr status --config config.yml --watch 10  # Refresh every 10 seconds
```

Press `Ctrl+C` to exit watch mode.

### Combining Flags

```bash
# Watch only drift, refresh every 3 seconds
baselinr status --config config.yml --drift-only --watch 3

# JSON output with limited runs
baselinr status --config config.yml --json --limit 5
```

## Output Interpretation

### Status Indicators

- 🟢 **Green (Healthy)**: No drift detected, no anomalies
- 🟡 **Yellow (Warning)**: Low/medium severity drift or anomalies detected
- 🔴 **Red (Critical)**: High severity drift detected

### Recent Runs Table

Columns:
- **Table**: Table name that was profiled
- **Schema**: Schema name (if applicable)
- **Duration**: How long profiling took (seconds/minutes/hours)
- **Rows**: Number of rows scanned
- **Metrics**: Count of distinct metrics collected
- **Anomalies**: Number of anomalies detected in this run
- **Status**: Health indicator (🟢/🟡/🔴)

### Drift Summary Table

Columns:
- **Table**: Table with active drift
- **Severity**: Drift severity (low/medium/high) - color coded
- **Type**: Type of drift detected:
  - `schema`: Schema changes (columns added/removed/renamed)
  - `volume`: Row count changes
  - `distribution`: Statistical distribution changes
  - `freshness`: Data freshness issues
- **Started**: When drift was first detected
- **Events**: Number of drift events for this table

## Integration

### Using with Scripts

```bash
# Check for high severity drift
baselinr status --config config.yml --json | jq '.drift_summary[] | select(.severity == "high")'

# Count runs in last 24h
baselinr status --config config.yml --json | jq '.runs | length'

# Get tables with drift
baselinr status --config config.yml --json | jq -r '.drift_summary[].table_name'
```

### CI/CD Integration

```bash
#!/bin/bash
# Fail build if high severity drift detected
DRIFT_COUNT=$(baselinr status --config config.yml --json | \
  jq '[.drift_summary[] | select(.severity == "high")] | length')

if [ "$DRIFT_COUNT" -gt 0 ]; then
  echo "ERROR: $DRIFT_COUNT high severity drift(s) detected"
  exit 1
fi
```

### Monitoring Dashboard

Use watch mode to create a live monitoring display:

```bash
# Terminal 1: Watch status
baselinr status --config config.yml --watch 5

# Terminal 2: Run profiling
baselinr profile --config config.yml
```

## Related Commands

For detailed information, use the query commands:

- **`baselinr query runs`**: Detailed run history with filters
- **`baselinr query drift`**: Detailed drift events with filters
- **`baselinr query run --run-id <id>`**: Detailed information about a specific run
- **`baselinr query table --table <name>`**: Historical profiling data for a table

## Troubleshooting

### No Runs Shown

If you see "No runs found", it means:
- No profiling runs in the last 24 hours
- Increase the time window by running profiling first

### No Drift Shown

If drift summary is empty:
- No drift events in the last 7 days
- This is normal if your data is stable
- Run `baselinr drift` to check for drift manually

### Watch Mode Not Working

If watch mode fails:
- Ensure Rich library is installed: `pip install rich>=13.0.0`
- Check that your terminal supports Rich output
- Use `--json` flag as fallback

### JSON Output Issues

If JSON parsing fails:
- Ensure output is valid JSON (redirect stderr: `2>/dev/null`)
- Use `jq` for pretty printing: `baselinr status --json | jq`

## See Also

- [Query Examples](QUERY_EXAMPLES.md) - Detailed query command reference
- [Drift Detection Guide](../guides/DRIFT_DETECTION.md) - Understanding drift detection
- [CLI Documentation](../../README.md) - Complete CLI reference


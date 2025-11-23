# Slack Alerts for Drift Detection

This guide explains how to set up Slack alerts for Baselinr drift detection and profiling events.

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Configuration](#configuration)
- [Alert Types](#alert-types)
- [Filtering Alerts](#filtering-alerts)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

## Overview

Baselinr can send real-time alerts to Slack channels when:
- **Data drift is detected** - Statistical changes in your data
- **Schema changes occur** - Columns added, removed, or type changes
- **Profiling failures happen** - Errors during profiling runs

Alerts are sent via Slack Incoming Webhooks and include rich formatting with:
- Color-coded severity levels
- Detailed metric information
- Timestamp tracking
- Customizable channels and usernames

## Setup

### 1. Create a Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Name your app (e.g., "Baselinr Alerts")
5. Select your workspace

### 2. Enable Incoming Webhooks

1. In your app settings, go to **"Incoming Webhooks"**
2. Toggle **"Activate Incoming Webhooks"** to **On**
3. Scroll down and click **"Add New Webhook to Workspace"**
4. Select the channel where alerts should be posted (e.g., `#data-alerts`)
5. Click **"Allow"**

### 3. Copy Webhook URL

1. You'll see a webhook URL like:
   ```
   https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
   ```
2. Copy this URL - you'll use it in your Baselinr configuration

### 4. Set Environment Variable (Recommended)

For security, store the webhook URL as an environment variable:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
```

Or add to your `.env` file:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
```

## Configuration

### Basic Configuration

Add the Slack hook to your `config.yml`:

```yaml
hooks:
  enabled: true
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
```

### Full Configuration

All available options:

```yaml
hooks:
  enabled: true
  hooks:
    - type: slack
      enabled: true                        # Enable/disable this hook
      webhook_url: ${SLACK_WEBHOOK_URL}    # Required: Slack webhook URL
      channel: "#data-alerts"              # Optional: Override default channel
      username: "Baselinr Bot"          # Optional: Bot display name
      min_severity: medium                 # Optional: Minimum severity (low, medium, high)
      alert_on_drift: true                 # Optional: Alert on drift events
      alert_on_schema_change: true         # Optional: Alert on schema changes
      alert_on_profiling_failure: true     # Optional: Alert on failures
      timeout: 10                          # Optional: HTTP timeout in seconds
```

### Configuration Options Explained

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `webhook_url` | string | *required* | Slack webhook URL from app setup |
| `channel` | string | *from webhook* | Override channel (e.g., "#alerts", "@username") |
| `username` | string | "Baselinr" | Display name for the bot |
| `min_severity` | string | "low" | Minimum drift severity to alert: "low", "medium", "high" |
| `alert_on_drift` | boolean | true | Send alerts for data drift events |
| `alert_on_schema_change` | boolean | true | Send alerts for schema changes |
| `alert_on_profiling_failure` | boolean | true | Send alerts for profiling failures |
| `timeout` | integer | 10 | HTTP request timeout in seconds |

## Alert Types

### Data Drift Alert

Sent when statistical drift is detected in your data:

**Example Alert:**
```
🚨 Data Drift Detected

Severity: HIGH
Table: orders
Column: total_amount
Metric: mean
Baseline Value: 100.50
Current Value: 150.75
Change: +50.0%
Timestamp: 2025-11-16 14:30:00 UTC
```

**Severity Indicators:**
- 🚨 **High** (Red) - Change > 30%
- 🔶 **Medium** (Orange) - Change > 15%
- ⚠️ **Low** (Orange) - Change > 5%

### Schema Change Alert

Sent when table schema changes are detected:

**Example Alert:**
```
➕ Schema Change Detected

Table: users
Change Type: Column Added
Description: Column `email` was added
Timestamp: 2025-11-16 14:30:00 UTC
```

**Change Types:**
- ➕ **Column Added** - New column detected
- ➖ **Column Removed** - Column no longer present
- 🔄 **Type Changed** - Column data type modified

### Profiling Failure Alert

Sent when profiling fails:

**Example Alert:**
```
❌ Profiling Failed

Table: products
Run ID: run-12345
Error: Connection timeout after 30 seconds
Timestamp: 2025-11-16 14:30:00 UTC
```

## Filtering Alerts

### By Severity

Only alert on critical drift:

```yaml
hooks:
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      min_severity: high  # Only high severity drift
```

### By Event Type

Customize which events trigger alerts:

```yaml
hooks:
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      alert_on_drift: true          # Alert on drift
      alert_on_schema_change: false # Skip schema changes
      alert_on_profiling_failure: true  # Alert on failures
```

### Multiple Channels

Send different alerts to different channels:

```yaml
hooks:
  enabled: true
  hooks:
    # Critical alerts to #incidents
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_CRITICAL}
      channel: "#incidents"
      min_severity: high
      alert_on_drift: true
      alert_on_schema_change: false
      alert_on_profiling_failure: true
    
    # All drift to #data-quality
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_QUALITY}
      channel: "#data-quality"
      min_severity: low
      alert_on_drift: true
      alert_on_schema_change: true
      alert_on_profiling_failure: false
```

## Security Best Practices

### 1. Never Commit Webhook URLs

❌ **Don't do this:**
```yaml
webhook_url: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
```

✅ **Do this:**
```yaml
webhook_url: ${SLACK_WEBHOOK_URL}
```

### 2. Use Environment Variables

Store webhook URLs in environment variables or secret management systems:

```bash
# .env file (add to .gitignore)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### 3. Restrict Webhook Permissions

In Slack app settings:
- Limit to specific channels
- Use dedicated channels for alerts
- Regularly rotate webhook URLs

### 4. Use Different Webhooks Per Environment

```yaml
# config-dev.yml
hooks:
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_DEV}
      channel: "#dev-alerts"

# config-prod.yml
hooks:
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_PROD}
      channel: "#prod-alerts"
```

## Troubleshooting

### Alerts Not Appearing

1. **Check webhook URL** - Verify it's correct and not expired
2. **Check hook is enabled** - Both master switch and individual hook
3. **Check severity threshold** - May be filtering alerts
4. **Check logs** - Look for Slack-related errors

```bash
baselinr profile --config config.yml --verbose
```

### "requests library is required" Error

Install the requests library:

```bash
pip install requests
```

Or with Baselinr:
```bash
pip install "baselinr[slack]"  # If package includes extras
```

### Timeouts

Increase timeout if experiencing connection issues:

```yaml
hooks:
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      timeout: 30  # Increase from default 10 seconds
```

### Wrong Channel

If alerts go to wrong channel, specify explicitly:

```yaml
hooks:
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#correct-channel"  # Override webhook default
```

## Examples

### Example 1: Production Setup

```yaml
# config-prod.yml
environment: production

hooks:
  enabled: true
  hooks:
    # High-severity alerts to #incidents
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_INCIDENTS}
      channel: "#incidents"
      username: "Baselinr [PROD]"
      min_severity: high
      alert_on_drift: true
      alert_on_schema_change: false
      alert_on_profiling_failure: true
    
    # All events to #data-monitoring
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_MONITORING}
      channel: "#data-monitoring"
      username: "Baselinr [PROD]"
      min_severity: low
      alert_on_drift: true
      alert_on_schema_change: true
      alert_on_profiling_failure: false
    
    # Also log to stdout
    - type: logging
      log_level: INFO
    
    # Persist to database
    - type: sql
      connection:
        type: postgres
        host: db.example.com
        database: monitoring
        username: ${DB_USER}
        password: ${DB_PASSWORD}
      table_name: baselinr_events
```

### Example 2: Development Setup

```yaml
# config-dev.yml
environment: development

hooks:
  enabled: true
  hooks:
    # Single channel for all alerts
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_DEV}
      channel: "#dev-data-alerts"
      username: "Baselinr [DEV]"
      min_severity: low
      alert_on_drift: true
      alert_on_schema_change: true
      alert_on_profiling_failure: true
```

### Example 3: Schema Changes Only

```yaml
hooks:
  enabled: true
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#schema-changes"
      username: "Schema Monitor"
      alert_on_drift: false          # Skip drift
      alert_on_schema_change: true   # Only schema changes
      alert_on_profiling_failure: false  # Skip failures
```

### Example 4: Testing Configuration

Test your Slack alerts with a simple drift detection:

```bash
# 1. Set environment variable
export SLACK_WEBHOOK_URL="your-webhook-url"

# 2. Run profiling twice to generate baseline
baselinr profile --config config_slack_alerts.yml

# Wait a moment, then run again
baselinr profile --config config_slack_alerts.yml

# 3. Run drift detection
baselinr detect-drift --config config_slack_alerts.yml --dataset orders
```

## Integration with Orchestration

### Dagster

```python
from baselinr.events import EventBus, SlackAlertHook
from baselinr.drift import DriftDetector

@asset
def detect_drift():
    # Create event bus with Slack hook
    bus = EventBus()
    bus.register(SlackAlertHook(
        webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
        channel="#data-alerts",
        min_severity="medium"
    ))
    
    # Run drift detection
    detector = DriftDetector(
        storage_config=storage_config,
        drift_config=drift_config,
        event_bus=bus
    )
    
    report = detector.detect_drift("orders")
    return report
```

### Airflow

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from baselinr.events import EventBus, SlackAlertHook

def detect_drift_with_alerts():
    bus = EventBus()
    bus.register(SlackAlertHook(
        webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
        channel="#airflow-alerts"
    ))
    
    # Run drift detection
    detector = DriftDetector(
        storage_config=storage_config,
        event_bus=bus
    )
    detector.detect_drift("orders")

with DAG('drift_detection', schedule_interval='@daily') as dag:
    task = PythonOperator(
        task_id='detect_drift',
        python_callable=detect_drift_with_alerts
    )
```

## Related Documentation

- [Event and Hooks System](../architecture/EVENTS_AND_HOOKS.md)
- [Drift Detection Guide](DRIFT_DETECTION.md)
- [Configuration Schema](../../baselinr/config/schema.py)
- [Example Configuration](../../examples/config_slack_alerts.yml)

## Support

For issues or questions:
- Check logs for error messages
- Verify webhook URL is valid
- Test with Slack's webhook tester
- Review Baselinr logs with `--verbose` flag

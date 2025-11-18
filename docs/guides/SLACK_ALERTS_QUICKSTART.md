# Slack Alerts - Quick Start

Get Slack alerts for data drift in 5 minutes.

## Setup Steps

### 1. Get Your Slack Webhook URL

1. Go to https://api.slack.com/apps
2. Create a new app → "From scratch"
3. Enable "Incoming Webhooks"
4. Add webhook to your workspace
5. Copy the webhook URL

### 2. Set Environment Variable

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### 3. Configure Baselinr

Add to your `config.yml`:

```yaml
hooks:
  enabled: true
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#data-alerts"
      min_severity: medium  # low, medium, or high
```

### 4. Run Profiling

```bash
baselinr profile --config config.yml
```

Drift alerts will automatically be sent to your Slack channel! 🎉

## What You'll Get

### Drift Alerts
```
🚨 Data Drift Detected

Severity: HIGH
Table: orders
Column: total_amount
Metric: mean
Change: +50.0%
```

### Schema Change Alerts
```
➕ Schema Change Detected

Table: users
Change Type: Column Added
Description: Column `email` was added
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `webhook_url` | *required* | Your Slack webhook URL |
| `channel` | *from webhook* | Channel to post to (e.g., "#alerts") |
| `min_severity` | `low` | Filter: "low", "medium", or "high" |
| `alert_on_drift` | `true` | Alert on data drift |
| `alert_on_schema_change` | `true` | Alert on schema changes |
| `alert_on_profiling_failure` | `true` | Alert on failures |

## Examples

### Production Setup - Multiple Channels

```yaml
hooks:
  enabled: true
  hooks:
    # Critical alerts to #incidents
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_INCIDENTS}
      channel: "#incidents"
      min_severity: high
    
    # All alerts to #data-quality
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_QUALITY}
      channel: "#data-quality"
      min_severity: low
```

### Development Setup

```yaml
hooks:
  enabled: true
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_DEV}
      channel: "#dev-alerts"
      username: "Baselinr [DEV]"
```

## Need More Details?

See the [full Slack Alerts guide](SLACK_ALERTS.md) for:
- Advanced configuration
- Security best practices
- Troubleshooting
- Integration with orchestrators

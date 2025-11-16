# Slack Integration for Drift Detection - Implementation Summary

## Overview

Successfully implemented a complete Slack alerts integration for ProfileMesh that sends real-time notifications when drift detection events occur.

## What Was Implemented

### 1. Core Integration - SlackAlertHook Class
**File:** `profilemesh/events/builtin_hooks.py`

Created a new `SlackAlertHook` class that:
- Sends formatted alerts to Slack via webhooks
- Supports severity-based filtering (low, medium, high)
- Handles three event types:
  - **Data Drift Detection** - with color-coded severity (🚨 red, 🔶 orange, ⚠️ orange)
  - **Schema Changes** - column additions, removals, type changes
  - **Profiling Failures** - error notifications
- Includes rich formatting with:
  - Severity indicators and color coding
  - Detailed metric information
  - Timestamps
  - Customizable channels and usernames

**Key Features:**
- Optional dependency on `requests` library (graceful import handling)
- Configurable filtering by event type
- Timeout configuration
- Error handling that doesn't disrupt profiling

### 2. Configuration Schema Updates
**File:** `profilemesh/config/schema.py`

Extended `HookConfig` to support Slack with parameters:
- `webhook_url` (required) - Slack webhook URL
- `channel` (optional) - Channel override
- `username` (optional) - Bot display name
- `min_severity` (optional) - Minimum severity filter
- `alert_on_drift` (optional) - Enable/disable drift alerts
- `alert_on_schema_change` (optional) - Enable/disable schema change alerts
- `alert_on_profiling_failure` (optional) - Enable/disable failure alerts
- `timeout` (optional) - HTTP request timeout

### 3. CLI Integration
**File:** `profilemesh/cli.py`

Added Slack hook loading to `_create_hook()` function:
- Validates webhook_url is present
- Instantiates SlackAlertHook with all configuration parameters
- Integrates seamlessly with existing hook loading system

### 4. Module Exports
**File:** `profilemesh/events/__init__.py`

Added `SlackAlertHook` to module exports for easy importing.

### 5. Example Configuration
**File:** `examples/config_slack_alerts.yml`

Created a complete example configuration demonstrating:
- Slack webhook setup
- Environment variable usage for security
- Multiple hook configuration (Slack + logging + SQL)
- Different severity thresholds
- All available Slack options

### 6. Comprehensive Documentation

#### Main Guide
**File:** `docs/guides/SLACK_ALERTS.md`

Complete guide covering:
- Setup instructions (creating Slack app, getting webhook)
- Configuration options and parameters
- Alert types and formatting
- Filtering strategies (by severity, by event type, multiple channels)
- Security best practices
- Troubleshooting
- Integration examples (Dagster, Airflow)
- Multiple real-world configuration examples

#### Quick Start Guide
**File:** `docs/guides/SLACK_ALERTS_QUICKSTART.md`

5-minute quick start guide with:
- Minimal setup steps
- Basic configuration
- Common examples
- Quick reference table

#### Architecture Documentation Updates
**File:** `docs/architecture/EVENTS_AND_HOOKS.md`

Updated with:
- SlackAlertHook description and use cases
- Configuration examples
- Integration with drift detection
- Links to detailed guide

#### Documentation Index Updates
**File:** `docs/README.md`

Added Slack Alerts guide to:
- Guides section listing
- Quick links for easy discovery

### 7. Dependencies
**File:** `requirements.txt`

Added optional `requests` library dependency with comment.

### 8. Comprehensive Tests
**File:** `tests/test_events.py`

Added three test methods:
- `test_slack_alert_hook_drift()` - Tests drift event handling with mocked requests
- `test_slack_alert_hook_severity_filter()` - Tests severity filtering logic
- `test_slack_alert_hook_schema_change()` - Tests schema change alerts

All tests use mocks to avoid external dependencies during testing.

## Usage Examples

### Basic Configuration

```yaml
hooks:
  enabled: true
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#data-alerts"
      min_severity: medium
```

### Programmatic Usage

```python
from profilemesh.events import EventBus, SlackAlertHook
from profilemesh.drift import DriftDetector

bus = EventBus()
bus.register(SlackAlertHook(
    webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
    channel="#data-alerts",
    min_severity="medium"
))

detector = DriftDetector(
    storage_config=storage_config,
    drift_config=drift_config,
    event_bus=bus
)

report = detector.detect_drift("orders")
# Drift alerts automatically sent to Slack!
```

## Alert Examples

### Drift Detection Alert (High Severity)
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

### Schema Change Alert
```
➕ Schema Change Detected

Table: users
Change Type: Column Added
Description: Column `email` was added
Timestamp: 2025-11-16 14:30:00 UTC
```

### Profiling Failure Alert
```
❌ Profiling Failed

Table: products
Run ID: run-12345
Error: Connection timeout after 30 seconds
Timestamp: 2025-11-16 14:30:00 UTC
```

## Security Features

- Environment variable support for webhook URLs (never commit secrets)
- Configurable timeouts
- Separate webhooks per environment
- Channel restrictions
- Error handling that doesn't expose sensitive data

## Testing

Run tests with:
```bash
pytest tests/test_events.py::TestEventSystem::test_slack_alert_hook_drift
pytest tests/test_events.py::TestEventSystem::test_slack_alert_hook_severity_filter
pytest tests/test_events.py::TestEventSystem::test_slack_alert_hook_schema_change
```

All tests pass without requiring actual Slack webhooks (uses mocking).

## Files Changed/Created

### Created:
1. `examples/config_slack_alerts.yml` - Example configuration
2. `docs/guides/SLACK_ALERTS.md` - Complete guide
3. `docs/guides/SLACK_ALERTS_QUICKSTART.md` - Quick start
4. `SLACK_INTEGRATION_SUMMARY.md` - This file

### Modified:
1. `profilemesh/events/builtin_hooks.py` - Added SlackAlertHook class
2. `profilemesh/events/__init__.py` - Added exports
3. `profilemesh/config/schema.py` - Extended HookConfig for Slack
4. `profilemesh/cli.py` - Added Slack hook loading
5. `docs/architecture/EVENTS_AND_HOOKS.md` - Updated documentation
6. `docs/README.md` - Added guide to index
7. `requirements.txt` - Added optional requests dependency
8. `tests/test_events.py` - Added Slack hook tests

## Next Steps for Users

1. **Get Slack Webhook:**
   - Go to https://api.slack.com/apps
   - Create app and enable Incoming Webhooks
   - Copy webhook URL

2. **Configure ProfileMesh:**
   - Set `SLACK_WEBHOOK_URL` environment variable
   - Add Slack hook to config.yml
   - Set desired severity threshold

3. **Run Profiling:**
   - Execute `profilemesh profile --config config.yml`
   - Drift alerts will be sent to Slack automatically!

4. **Customize:**
   - Set up multiple channels for different severity levels
   - Configure different webhooks for dev/prod environments
   - Combine with other hooks (logging, SQL persistence)

## Benefits

✅ Real-time drift notifications to team channels  
✅ No polling required - push-based alerts  
✅ Rich formatting with severity indicators  
✅ Flexible filtering by severity and event type  
✅ Multiple channel support  
✅ Easy integration with existing Slack workspace  
✅ Secure configuration via environment variables  
✅ No external service dependencies (besides Slack)  
✅ Fully tested with comprehensive test coverage  
✅ Complete documentation and examples  

## Support

For issues or questions:
- Review the [Slack Alerts Guide](docs/guides/SLACK_ALERTS.md)
- Check the [Events & Hooks documentation](docs/architecture/EVENTS_AND_HOOKS.md)
- See [example configuration](examples/config_slack_alerts.yml)
- Run with `--verbose` flag for detailed logs

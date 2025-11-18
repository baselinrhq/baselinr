# Event and Alert Hook System

Baselinr includes a lightweight, pluggable event emission and alert hook system that allows you to react to runtime events such as data drift detection, schema changes, and profiling lifecycle events.

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Event Types](#event-types)
- [Built-in Hooks](#built-in-hooks)
- [Configuration](#configuration)
- [Custom Hooks](#custom-hooks)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

## Overview

The event system enables Baselinr to:

- **Emit events** during profiling and drift detection operations
- **Process events** through multiple registered hooks
- **Alert or persist** events based on your configuration
- **Remain orchestration-agnostic** - the core tool has no external dependencies

Events are emitted in-memory and dispatched synchronously to all registered hooks. Hooks can fail independently without stopping other hooks or the profiling process.

## Core Concepts

### EventBus

The `EventBus` is the central component that manages hook registration and event emission:

```python
from baselinr.events import EventBus, LoggingAlertHook

# Create event bus
bus = EventBus()

# Register hooks
bus.register(LoggingAlertHook())

# Emit event
bus.emit(event)
```

### Events

Events are dataclasses that represent specific occurrences in the profiling lifecycle:

```python
from baselinr.events import DataDriftDetected
from datetime import datetime

event = DataDriftDetected(
    event_type="DataDriftDetected",
    timestamp=datetime.utcnow(),
    table="users",
    column="age",
    metric="mean",
    baseline_value=30.5,
    current_value=35.2,
    change_percent=15.4,
    drift_severity="high",
    metadata={}
)
```

### Alert Hooks

Hooks are objects that implement the `AlertHook` protocol:

```python
from baselinr.events import AlertHook, BaseEvent

class MyCustomHook:
    def handle_event(self, event: BaseEvent) -> None:
        # Process the event
        print(f"Event: {event.event_type}")
```

## Event Types

### DataDriftDetected

Emitted when data drift is detected between profiling runs:

**Fields:**
- `table`: Table name
- `column`: Column name
- `metric`: Metric name (e.g., "mean", "count", "null_percent")
- `baseline_value`: Value from baseline run
- `current_value`: Value from current run
- `change_percent`: Percentage change
- `drift_severity`: Severity level ("low", "medium", "high")

**Example:**
```python
DataDriftDetected(
    event_type="DataDriftDetected",
    timestamp=datetime.utcnow(),
    table="orders",
    column="total_amount",
    metric="mean",
    baseline_value=100.50,
    current_value=150.75,
    change_percent=50.0,
    drift_severity="high",
    metadata={}
)
```

### SchemaChangeDetected

Emitted when schema changes are detected:

**Fields:**
- `table`: Table name
- `change_type`: Type of change ("column_added", "column_removed", "type_changed")
- `column`: Column name (if applicable)
- `old_type`: Previous data type (for type changes)
- `new_type`: New data type (for type changes)

**Example:**
```python
SchemaChangeDetected(
    event_type="SchemaChangeDetected",
    timestamp=datetime.utcnow(),
    table="users",
    change_type="column_added",
    column="email",
    metadata={}
)
```

### ProfilingStarted

Emitted when profiling begins for a table:

**Fields:**
- `table`: Table name
- `run_id`: Unique run identifier

### ProfilingCompleted

Emitted when profiling completes successfully:

**Fields:**
- `table`: Table name
- `run_id`: Unique run identifier
- `row_count`: Number of rows profiled
- `column_count`: Number of columns profiled
- `duration_seconds`: Profiling duration

### ProfilingFailed

Emitted when profiling fails:

**Fields:**
- `table`: Table name
- `run_id`: Unique run identifier
- `error`: Error message

## Built-in Hooks

### LoggingAlertHook

Logs events to stdout using Python's logging module:

```yaml
hooks:
  enabled: true
  hooks:
    - type: logging
      log_level: INFO
```

**Use Case:** Development, debugging, simple monitoring

### SQLEventHook

Persists events to any SQL database (Postgres, MySQL, SQLite):

```yaml
hooks:
  enabled: true
  hooks:
    - type: sql
      table_name: baselinr_events
      connection:
        type: postgres
        host: localhost
        port: 5432
        database: monitoring
        username: user
        password: pass
```

**Use Case:** Historical event tracking, audit trails

### SnowflakeEventHook

Persists events to Snowflake with VARIANT support for metadata:

```yaml
hooks:
  enabled: true
  hooks:
    - type: snowflake
      table_name: baselinr_events
      connection:
        type: snowflake
        account: myaccount
        database: monitoring
        warehouse: compute_wh
        username: user
        password: pass
```

**Use Case:** Enterprise data warehousing, Snowflake-native monitoring

### SlackAlertHook

Sends formatted alerts to Slack channels when drift or other events occur:

```yaml
hooks:
  enabled: true
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#data-alerts"
      username: "Baselinr Bot"
      min_severity: medium
      alert_on_drift: true
      alert_on_schema_change: true
      alert_on_profiling_failure: true
      timeout: 10
```

**Use Case:** Real-time team notifications, incident response, monitoring dashboards

**Features:**
- Severity-based filtering (low, medium, high)
- Rich formatted messages with color coding
- Separate alerts for drift, schema changes, and failures
- Configurable channel and username
- Environment variable support for webhook URLs

## Configuration

### Master Switch

Enable or disable all hooks with the master switch:

```yaml
hooks:
  enabled: true  # Set to false to disable all hooks
  hooks:
    # ... hook configurations
```

### Multiple Hooks

You can register multiple hooks that will all receive events:

```yaml
hooks:
  enabled: true
  hooks:
    # Log all events
    - type: logging
      log_level: INFO
    
    # Persist critical events to database
    - type: sql
      table_name: baselinr_events
      connection:
        type: postgres
        host: localhost
        database: monitoring
        username: user
        password: pass
    
    # Send to custom webhook
    - type: custom
      module: my_hooks
      class_name: WebhookAlertHook
      params:
        webhook_url: https://api.example.com/alerts
```

### Selective Enablement

Disable individual hooks without removing their configuration:

```yaml
hooks:
  enabled: true
  hooks:
    - type: logging
      enabled: true  # Active
    
    - type: sql
      enabled: false  # Temporarily disabled
      connection:
        # ... config preserved
```

## Custom Hooks

Create custom hooks by implementing the `AlertHook` protocol:

### 1. Create Hook Class

```python
# my_hooks.py
from baselinr.events import BaseEvent
import requests

class WebhookAlertHook:
    """Send events to a webhook endpoint."""
    
    def __init__(self, webhook_url: str, auth_token: str = None):
        self.webhook_url = webhook_url
        self.auth_token = auth_token
    
    def handle_event(self, event: BaseEvent) -> None:
        """Send event to webhook."""
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        payload = {
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=5
            )
            response.raise_for_status()
        except Exception as e:
            # Log but don't fail - hook failures shouldn't stop profiling
            print(f"Webhook alert failed: {e}")
```

### 2. Configure Hook

```yaml
hooks:
  enabled: true
  hooks:
    - type: custom
      module: my_hooks
      class_name: WebhookAlertHook
      params:
        webhook_url: https://api.example.com/alerts
        auth_token: ${WEBHOOK_AUTH_TOKEN}  # Use environment variable
```

### 3. Advanced Custom Hook Example

```python
# my_hooks.py
from baselinr.events import BaseEvent, DataDriftDetected
import smtplib
from email.mime.text import MIMEText

class EmailAlertHook:
    """Send email alerts for high-severity drift."""
    
    def __init__(self, smtp_host: str, smtp_port: int, 
                 from_email: str, to_emails: list, 
                 severity_threshold: str = "high"):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.to_emails = to_emails
        self.severity_threshold = severity_threshold
    
    def handle_event(self, event: BaseEvent) -> None:
        """Send email for high-severity drift events."""
        # Only handle drift events
        if not isinstance(event, DataDriftDetected):
            return
        
        # Only alert on high severity (or higher)
        if event.drift_severity != self.severity_threshold:
            return
        
        # Compose email
        subject = f"[ALERT] Data Drift Detected: {event.table}.{event.column}"
        body = f"""
        High-severity data drift detected:
        
        Table: {event.table}
        Column: {event.column}
        Metric: {event.metric}
        
        Baseline: {event.baseline_value}
        Current: {event.current_value}
        Change: {event.change_percent:+.2f}%
        
        Severity: {event.drift_severity.upper()}
        """
        
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = ", ".join(self.to_emails)
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.send_message(msg)
        except Exception as e:
            print(f"Email alert failed: {e}")
```

## Usage Examples

### Example 1: Basic Logging

```yaml
# config.yml
hooks:
  enabled: true
  hooks:
    - type: logging
      log_level: INFO
```

```bash
baselinr profile --config config.yml
```

Output:
```
[ALERT] ProfilingStarted: {'table': 'users', 'run_id': '...'}
[ALERT] ProfilingCompleted: {'table': 'users', 'row_count': 1000, ...}
```

### Example 2: Database Persistence

```yaml
# config.yml
hooks:
  enabled: true
  hooks:
    - type: sql
      table_name: baselinr_events
      connection:
        type: sqlite
        database: monitoring
        filepath: ./monitoring.db
```

Events are automatically stored in the `baselinr_events` table:

```sql
SELECT * FROM baselinr_events 
WHERE event_type = 'DataDriftDetected'
ORDER BY timestamp DESC;
```

### Example 3: Multi-Environment Setup

```yaml
# config-dev.yml
hooks:
  enabled: true
  hooks:
    - type: logging  # Dev: just log
      log_level: DEBUG

# config-prod.yml
hooks:
  enabled: true
  hooks:
    - type: logging  # Still log
      log_level: WARNING
    
    - type: snowflake  # Persist in production
      table_name: prod.monitoring.baselinr_events
      connection:
        type: snowflake
        account: ${SNOWFLAKE_ACCOUNT}
        database: monitoring
        warehouse: compute_wh
        username: ${SNOWFLAKE_USER}
        password: ${SNOWFLAKE_PASSWORD}
```

### Example 4: Slack Alerts for Drift Detection

Configure Slack alerts using the built-in SlackAlertHook:

```yaml
# config.yml
hooks:
  enabled: true
  hooks:
    - type: slack
      webhook_url: ${SLACK_WEBHOOK_URL}
      channel: "#data-alerts"
      username: "Baselinr Bot"
      min_severity: medium
      alert_on_drift: true
      alert_on_schema_change: true
      alert_on_profiling_failure: true
```

Or use it programmatically:

```python
from baselinr.events import EventBus, SlackAlertHook
from baselinr.drift import DriftDetector
import os

# Create event bus with Slack hook
bus = EventBus()
bus.register(SlackAlertHook(
    webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
    channel="#data-alerts",
    min_severity="medium"
))

# Run drift detection with Slack alerts
detector = DriftDetector(
    storage_config=storage_config,
    drift_config=drift_config,
    event_bus=bus
)

report = detector.detect_drift("orders")
# Drift events automatically sent to Slack
```

See [Slack Alerts Guide](../guides/SLACK_ALERTS.md) for detailed setup instructions.

## Best Practices

### 1. **Use Master Switch for Environments**

Enable hooks in production, disable in development:

```yaml
hooks:
  enabled: ${ENABLE_HOOKS:-false}  # Defaults to false
```

### 2. **Handle Hook Failures Gracefully**

Hooks should catch and log exceptions, not raise them:

```python
def handle_event(self, event: BaseEvent) -> None:
    try:
        # Process event
        self._send_alert(event)
    except Exception as e:
        logger.error(f"Alert failed: {e}")
        # Don't re-raise - let profiling continue
```

### 3. **Filter Events in Hooks**

Don't process every event if you only care about specific types:

```python
def handle_event(self, event: BaseEvent) -> None:
    if not isinstance(event, DataDriftDetected):
        return  # Skip non-drift events
    
    if event.drift_severity != "high":
        return  # Only alert on high severity
    
    # Process high-severity drift
    self._send_alert(event)
```

### 4. **Use Async for External Calls**

For production systems with external APIs, consider async:

```python
import asyncio
import aiohttp

class AsyncWebhookHook:
    def handle_event(self, event: BaseEvent) -> None:
        # Fire and forget
        asyncio.create_task(self._send_async(event))
    
    async def _send_async(self, event: BaseEvent):
        async with aiohttp.ClientSession() as session:
            await session.post(self.webhook_url, json=event.to_dict())
```

### 5. **Monitor Hook Performance**

Log hook execution time for debugging:

```python
import time

def handle_event(self, event: BaseEvent) -> None:
    start = time.time()
    try:
        self._process_event(event)
    finally:
        duration = time.time() - start
        logger.debug(f"Hook processed event in {duration:.3f}s")
```

### 6. **Use SQL Schema for Persistence**

When using SQL/Snowflake hooks, create the events table first:

```sql
-- Run this before enabling SQL hooks
CREATE TABLE baselinr_events (
    event_id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    table_name VARCHAR(255),
    column_name VARCHAR(255),
    metric_name VARCHAR(100),
    baseline_value FLOAT,
    current_value FLOAT,
    change_percent FLOAT,
    drift_severity VARCHAR(20),
    timestamp TIMESTAMP NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

See `baselinr/storage/schema.sql` and `baselinr/storage/schema_snowflake.sql` for full schemas.

## Integration with Orchestrators

### Dagster

```python
# dagster_repository.py
from baselinr.events import EventBus, LoggingAlertHook
from baselinr.profiling import ProfileEngine

@asset
def profile_users():
    config = load_config()
    
    # Create event bus
    bus = EventBus()
    bus.register(LoggingAlertHook())
    
    # Profile with events
    engine = ProfileEngine(config, event_bus=bus)
    results = engine.profile()
    
    return results
```

### Airflow

```python
# dags/profiling_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from baselinr.events import EventBus, SQLEventHook
from baselinr.profiling import ProfileEngine

def profile_with_alerts():
    config = load_config()
    
    # Register hooks
    bus = EventBus()
    bus.register(SQLEventHook(engine=get_airflow_db_engine()))
    
    engine = ProfileEngine(config, event_bus=bus)
    engine.profile()

dag = DAG('profile_users', schedule_interval='@daily')
task = PythonOperator(
    task_id='profile',
    python_callable=profile_with_alerts,
    dag=dag
)
```

## Troubleshooting

### Hooks Not Firing

1. Check `hooks.enabled` is set to `true`
2. Verify individual hook `enabled` fields
3. Check logs for hook registration messages

### Event Persistence Failing

1. Ensure the `baselinr_events` table exists
2. Verify database connection configuration
3. Check database user has INSERT permissions
4. Review hook error logs

### Custom Hook Not Loading

1. Verify module path is correct and importable
2. Check class name spelling
3. Ensure hook implements `handle_event(event: BaseEvent)` method
4. Review import errors in logs

## Future Enhancements

Planned improvements to the event system:

- **Event Filtering**: Configure which events each hook receives
- **Async Hooks**: Native async/await support for non-blocking hooks
- **Event Batching**: Batch multiple events for efficient persistence
- **Retry Logic**: Automatic retry for failed hook executions
- **Rate Limiting**: Prevent alert fatigue with configurable limits
- **Event Streaming**: Kafka/Kinesis integration for event streams

## Related Documentation

- [Configuration Guide](README.md#configuration)
- [Drift Detection](../guides/DRIFT_DETECTION.md)
- [Storage Schema](baselinr/storage/schema.sql)


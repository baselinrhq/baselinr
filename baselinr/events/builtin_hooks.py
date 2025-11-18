"""
Built-in alert hook implementations for Baselinr.

Provides commonly used hooks for logging and persistence.
"""

import json
import logging
import uuid
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .events import BaseEvent

logger = logging.getLogger(__name__)


class LoggingAlertHook:
    """
    Simple logging hook that prints events to stdout.

    This hook is useful for development and debugging. Events are logged
    at INFO level with structured information.
    """

    def __init__(self, log_level: str = "INFO"):
        """
        Initialize the logging hook.

        Args:
            log_level: The logging level to use (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger = logging.getLogger(f"{__name__}.LoggingAlertHook")

    def handle_event(self, event: BaseEvent) -> None:
        """
        Log the event.

        Args:
            event: The event to log
        """
        self.logger.log(self.log_level, f"[ALERT] {event.event_type}: {event.metadata}")


class SnowflakeEventHook:
    """
    Hook that persists events to a Snowflake table.

    This hook writes all events to a `baselinr_events` table for
    historical tracking and analysis. The table must exist before using
    this hook.

    Table Schema:
        CREATE TABLE baselinr_events (
            event_id VARCHAR PRIMARY KEY,
            event_type VARCHAR NOT NULL,
            run_id VARCHAR,
            table_name VARCHAR,
            column_name VARCHAR,
            metric_name VARCHAR,
            baseline_value FLOAT,
            current_value FLOAT,
            change_percent FLOAT,
            drift_severity VARCHAR,
            timestamp TIMESTAMP NOT NULL,
            metadata VARIANT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """

    def __init__(self, engine: Engine, table_name: str = "baselinr_events"):
        """
        Initialize the Snowflake event hook.

        Args:
            engine: SQLAlchemy engine connected to Snowflake
            table_name: Name of the table to write events to
        """
        self.engine = engine
        self.table_name = table_name

    def handle_event(self, event: BaseEvent) -> None:
        """
        Persist the event to Snowflake.

        Args:
            event: The event to persist
        """
        try:
            event_id = str(uuid.uuid4())

            # Extract common fields from metadata
            metadata = event.metadata or {}
            table_name = metadata.get("table")
            column_name = metadata.get("column")
            metric_name = metadata.get("metric")
            baseline_value = metadata.get("baseline_value")
            current_value = metadata.get("current_value")
            change_percent = metadata.get("change_percent")
            drift_severity = metadata.get("drift_severity")
            run_id = metadata.get("run_id")

            # Convert metadata to JSON string for VARIANT column
            metadata_json = json.dumps(metadata)

            sql = text(
                f"""
                INSERT INTO {self.table_name}
                (event_id, event_type, run_id, table_name, column_name, metric_name,
                 baseline_value, current_value, change_percent, drift_severity,
                 timestamp, metadata)
                VALUES (
                    :event_id, :event_type, :run_id, :table_name, :column_name, :metric_name,
                    :baseline_value, :current_value, :change_percent, :drift_severity,
                    :timestamp, PARSE_JSON(:metadata)
                )
            """
            )

            with self.engine.begin() as conn:
                conn.execute(
                    sql,
                    {
                        "event_id": event_id,
                        "event_type": event.event_type,
                        "run_id": run_id,
                        "table_name": table_name,
                        "column_name": column_name,
                        "metric_name": metric_name,
                        "baseline_value": baseline_value,
                        "current_value": current_value,
                        "change_percent": change_percent,
                        "drift_severity": drift_severity,
                        "timestamp": event.timestamp,
                        "metadata": metadata_json,
                    },
                )

            logger.debug(f"Persisted event {event_id} to {self.table_name}")

        except Exception as e:
            logger.error(f"Failed to persist event to Snowflake: {e}", exc_info=True)
            raise


class SQLEventHook:
    """
    Generic SQL hook that persists events to any SQL database.

    This hook is more flexible than SnowflakeEventHook and works with
    any database supported by SQLAlchemy (Postgres, MySQL, SQLite, etc.).

    Table Schema:
        CREATE TABLE baselinr_events (
            event_id VARCHAR(36) PRIMARY KEY,
            event_type VARCHAR(100) NOT NULL,
            run_id VARCHAR(36),
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
    """

    def __init__(self, engine: Engine, table_name: str = "baselinr_events"):
        """
        Initialize the SQL event hook.

        Args:
            engine: SQLAlchemy engine
            table_name: Name of the table to write events to
        """
        self.engine = engine
        self.table_name = table_name

    def handle_event(self, event: BaseEvent) -> None:
        """
        Persist the event to the database.

        Args:
            event: The event to persist
        """
        try:
            event_id = str(uuid.uuid4())

            # Extract common fields from metadata
            metadata = event.metadata or {}
            table_name = metadata.get("table")
            column_name = metadata.get("column")
            metric_name = metadata.get("metric")
            baseline_value = metadata.get("baseline_value")
            current_value = metadata.get("current_value")
            change_percent = metadata.get("change_percent")
            drift_severity = metadata.get("drift_severity")
            run_id = metadata.get("run_id")

            # Convert metadata to JSON string
            metadata_json = json.dumps(metadata)

            sql = text(
                f"""
                INSERT INTO {self.table_name}
                (event_id, event_type, run_id, table_name, column_name, metric_name,
                 baseline_value, current_value, change_percent, drift_severity,
                 timestamp, metadata)
                VALUES (
                    :event_id, :event_type, :run_id, :table_name, :column_name, :metric_name,
                    :baseline_value, :current_value, :change_percent, :drift_severity,
                    :timestamp, :metadata
                )
            """
            )

            with self.engine.begin() as conn:
                conn.execute(
                    sql,
                    {
                        "event_id": event_id,
                        "event_type": event.event_type,
                        "run_id": run_id,
                        "table_name": table_name,
                        "column_name": column_name,
                        "metric_name": metric_name,
                        "baseline_value": baseline_value,
                        "current_value": current_value,
                        "change_percent": change_percent,
                        "drift_severity": drift_severity,
                        "timestamp": event.timestamp,
                        "metadata": metadata_json,
                    },
                )

            logger.debug(f"Persisted event {event_id} to {self.table_name}")

        except Exception as e:
            logger.error(f"Failed to persist event to database: {e}", exc_info=True)
            raise


class SlackAlertHook:
    """
    Hook that sends drift detection alerts to Slack.

    This hook sends formatted messages to a Slack channel via webhook when
    drift detection events occur. It can filter by minimum severity and
    event types.

    To get a webhook URL:
        1. Go to https://api.slack.com/apps
        2. Create a new app or select existing
        3. Enable Incoming Webhooks
        4. Add webhook to workspace
        5. Copy the webhook URL
    """

    def __init__(
        self,
        webhook_url: str,
        channel: Optional[str] = None,
        username: str = "Baselinr",
        min_severity: str = "low",
        alert_on_drift: bool = True,
        alert_on_schema_change: bool = True,
        alert_on_profiling_failure: bool = True,
        timeout: int = 10,
    ):
        """
        Initialize the Slack alert hook.

        Args:
            webhook_url: Slack webhook URL
            channel: Optional channel override (e.g., "#alerts")
            username: Bot username (default: "Baselinr")
            min_severity: Minimum severity for drift alerts ("low", "medium", "high")
            alert_on_drift: Send alerts for drift detection events
            alert_on_schema_change: Send alerts for schema changes
            alert_on_profiling_failure: Send alerts for profiling failures
            timeout: Request timeout in seconds
        """
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.min_severity = min_severity
        self.alert_on_drift = alert_on_drift
        self.alert_on_schema_change = alert_on_schema_change
        self.alert_on_profiling_failure = alert_on_profiling_failure
        self.timeout = timeout
        self.severity_order = {"low": 1, "medium": 2, "high": 3}

        # Import here to avoid hard dependency
        try:
            import requests  # type: ignore[import-untyped]

            self.requests = requests
        except ImportError:
            raise ImportError(
                "requests library is required for SlackAlertHook. "
                "Install with: pip install requests"
            )

    def handle_event(self, event: BaseEvent) -> None:
        """
        Handle event and send to Slack if appropriate.

        Args:
            event: The event to handle
        """
        from .events import DataDriftDetected, ProfilingFailed, SchemaChangeDetected

        try:
            # Filter based on event type
            if isinstance(event, DataDriftDetected) and self.alert_on_drift:
                # Check severity threshold
                event_severity = self.severity_order.get(event.drift_severity, 0)
                min_severity = self.severity_order.get(self.min_severity, 0)

                if event_severity >= min_severity:
                    self._send_drift_alert(event)

            elif isinstance(event, SchemaChangeDetected) and self.alert_on_schema_change:
                self._send_schema_change_alert(event)

            elif isinstance(event, ProfilingFailed) and self.alert_on_profiling_failure:
                self._send_profiling_failure_alert(event)

        except Exception as e:
            # Log but don't raise - hook failures shouldn't stop profiling
            logger.error(f"Failed to send Slack alert: {e}", exc_info=True)

    def _send_drift_alert(self, event) -> None:
        """Send drift detection alert to Slack."""

        # Determine emoji based on severity
        emoji = {"low": "⚠️", "medium": "🔶", "high": "🚨"}.get(event.drift_severity, "⚠️")

        # Determine color based on severity
        color = {
            "low": "#FFA500",  # Orange
            "medium": "#FF8C00",  # Dark Orange
            "high": "#FF0000",  # Red
        }.get(event.drift_severity, "#FFA500")

        # Format change percentage
        change_sign = "+" if event.change_percent >= 0 else ""
        change_str = (
            f"{change_sign}{event.change_percent:.1f}%"
            if event.change_percent is not None
            else "N/A"
        )

        payload = {
            "username": self.username,
            "text": f"{emoji} *Data Drift Detected*",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {"title": "Severity", "value": event.drift_severity.upper(), "short": True},
                        {"title": "Table", "value": f"`{event.table}`", "short": True},
                        {"title": "Column", "value": f"`{event.column}`", "short": True},
                        {"title": "Metric", "value": event.metric, "short": True},
                        {
                            "title": "Baseline Value",
                            "value": (
                                f"{event.baseline_value:.2f}"
                                if isinstance(event.baseline_value, (int, float))
                                else str(event.baseline_value)
                            ),
                            "short": True,
                        },
                        {
                            "title": "Current Value",
                            "value": (
                                f"{event.current_value:.2f}"
                                if isinstance(event.current_value, (int, float))
                                else str(event.current_value)
                            ),
                            "short": True,
                        },
                        {"title": "Change", "value": change_str, "short": True},
                        {
                            "title": "Timestamp",
                            "value": event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True,
                        },
                    ],
                    "footer": "Baselinr Drift Detection",
                    "ts": int(event.timestamp.timestamp()),
                }
            ],
        }

        if self.channel:
            payload["channel"] = self.channel

        self._send_to_slack(payload)

    def _send_schema_change_alert(self, event) -> None:
        """Send schema change alert to Slack."""

        # Determine emoji based on change type
        emoji = {"column_added": "➕", "column_removed": "➖", "type_changed": "🔄"}.get(
            event.change_type, "🔄"
        )

        # Build description
        if event.change_type == "type_changed":
            old_t = event.old_type
            new_t = event.new_type
            description = f"Column `{event.column}` type changed from `{old_t}` to `{new_t}`"
        elif event.change_type == "column_added":
            description = f"Column `{event.column}` was added"
        elif event.change_type == "column_removed":
            description = f"Column `{event.column}` was removed"
        else:
            description = f"Schema change: {event.change_type}"

        payload = {
            "username": self.username,
            "text": f"{emoji} *Schema Change Detected*",
            "attachments": [
                {
                    "color": "#36a64f",  # Green
                    "fields": [
                        {"title": "Table", "value": f"`{event.table}`", "short": True},
                        {
                            "title": "Change Type",
                            "value": event.change_type.replace("_", " ").title(),
                            "short": True,
                        },
                        {"title": "Description", "value": description, "short": False},
                        {
                            "title": "Timestamp",
                            "value": event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True,
                        },
                    ],
                    "footer": "Baselinr Schema Detection",
                    "ts": int(event.timestamp.timestamp()),
                }
            ],
        }

        if self.channel:
            payload["channel"] = self.channel

        self._send_to_slack(payload)

    def _send_profiling_failure_alert(self, event) -> None:
        """Send profiling failure alert to Slack."""

        payload = {
            "username": self.username,
            "text": "❌ *Profiling Failed*",
            "attachments": [
                {
                    "color": "#FF0000",  # Red
                    "fields": [
                        {"title": "Table", "value": f"`{event.table}`", "short": True},
                        {"title": "Run ID", "value": event.run_id, "short": True},
                        {"title": "Error", "value": f"```{event.error}```", "short": False},
                        {
                            "title": "Timestamp",
                            "value": event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True,
                        },
                    ],
                    "footer": "Baselinr Profiling",
                    "ts": int(event.timestamp.timestamp()),
                }
            ],
        }

        if self.channel:
            payload["channel"] = self.channel

        self._send_to_slack(payload)

    def _send_to_slack(self, payload: dict) -> None:
        """
        Send payload to Slack webhook.

        Args:
            payload: Slack message payload
        """
        try:
            response = self.requests.post(self.webhook_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            logger.debug(f"Sent Slack alert: {payload.get('text', 'Unknown')}")
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            raise

"""
Tests for the event and alert hook system.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy import create_engine

from baselinr.events import (
    BaseEvent,
    DataDriftDetected,
    EventBus,
    LoggingAlertHook,
    ProfilingCompleted,
    ProfilingFailed,
    ProfilingStarted,
    SchemaChangeDetected,
    SQLEventHook,
)


class TestBaseEvent:
    """Test BaseEvent class."""

    def test_base_event_creation(self):
        """Test creating a base event."""
        event = BaseEvent(
            event_type="test_event", timestamp=datetime.utcnow(), metadata={"key": "value"}
        )

        assert event.event_type == "test_event"
        assert isinstance(event.timestamp, datetime)
        assert event.metadata == {"key": "value"}

    def test_base_event_to_dict(self):
        """Test converting base event to dict."""
        timestamp = datetime.utcnow()
        event = BaseEvent(event_type="test_event", timestamp=timestamp, metadata={"key": "value"})

        result = event.to_dict()

        assert result["event_type"] == "test_event"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["metadata"] == {"key": "value"}


class TestDataDriftDetected:
    """Test DataDriftDetected event."""

    def test_drift_event_creation(self):
        """Test creating a drift detection event."""
        event = DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="users",
            column="age",
            metric="mean",
            baseline_value=30.5,
            current_value=35.2,
            change_percent=15.4,
            drift_severity="medium",
            metadata={},
        )

        assert event.table == "users"
        assert event.column == "age"
        assert event.metric == "mean"
        assert event.baseline_value == 30.5
        assert event.current_value == 35.2
        assert event.change_percent == 15.4
        assert event.drift_severity == "medium"

    def test_drift_event_metadata_populated(self):
        """Test that drift event populates metadata from fields."""
        event = DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="users",
            column="age",
            metric="mean",
            baseline_value=30.5,
            current_value=35.2,
            change_percent=15.4,
            drift_severity="medium",
            metadata={},
        )

        assert event.metadata["table"] == "users"
        assert event.metadata["column"] == "age"
        assert event.metadata["metric"] == "mean"
        assert event.metadata["baseline_value"] == 30.5
        assert event.metadata["current_value"] == 35.2
        assert event.metadata["change_percent"] == 15.4
        assert event.metadata["drift_severity"] == "medium"


class TestSchemaChangeDetected:
    """Test SchemaChangeDetected event."""

    def test_schema_change_event_column_added(self):
        """Test schema change event for column addition."""
        event = SchemaChangeDetected(
            event_type="SchemaChangeDetected",
            timestamp=datetime.utcnow(),
            table="users",
            change_type="column_added",
            column="email",
            metadata={},
        )

        assert event.table == "users"
        assert event.change_type == "column_added"
        assert event.column == "email"
        assert event.metadata["table"] == "users"
        assert event.metadata["change_type"] == "column_added"

    def test_schema_change_event_type_changed(self):
        """Test schema change event for type change."""
        event = SchemaChangeDetected(
            event_type="SchemaChangeDetected",
            timestamp=datetime.utcnow(),
            table="users",
            change_type="type_changed",
            column="age",
            old_type="INTEGER",
            new_type="BIGINT",
            metadata={},
        )

        assert event.old_type == "INTEGER"
        assert event.new_type == "BIGINT"
        assert event.metadata["old_type"] == "INTEGER"
        assert event.metadata["new_type"] == "BIGINT"


class TestProfilingEvents:
    """Test profiling lifecycle events."""

    def test_profiling_started_event(self):
        """Test ProfilingStarted event."""
        event = ProfilingStarted(
            event_type="ProfilingStarted",
            timestamp=datetime.utcnow(),
            table="users",
            run_id="test-run-123",
            metadata={},
        )

        assert event.table == "users"
        assert event.run_id == "test-run-123"
        assert event.metadata["table"] == "users"
        assert event.metadata["run_id"] == "test-run-123"

    def test_profiling_completed_event(self):
        """Test ProfilingCompleted event."""
        event = ProfilingCompleted(
            event_type="ProfilingCompleted",
            timestamp=datetime.utcnow(),
            table="users",
            run_id="test-run-123",
            row_count=1000,
            column_count=10,
            duration_seconds=5.5,
            metadata={},
        )

        assert event.row_count == 1000
        assert event.column_count == 10
        assert event.duration_seconds == 5.5
        assert event.metadata["row_count"] == 1000

    def test_profiling_failed_event(self):
        """Test ProfilingFailed event."""
        event = ProfilingFailed(
            event_type="ProfilingFailed",
            timestamp=datetime.utcnow(),
            table="users",
            run_id="test-run-123",
            error="Connection timeout",
            metadata={},
        )

        assert event.error == "Connection timeout"
        assert event.metadata["error"] == "Connection timeout"


class TestEventBus:
    """Test EventBus functionality."""

    def test_event_bus_creation(self):
        """Test creating an event bus."""
        bus = EventBus()
        assert bus.hook_count == 0
        assert bus.event_count == 0

    def test_register_hook(self):
        """Test registering a hook."""
        bus = EventBus()
        hook = Mock()

        bus.register(hook)

        assert bus.hook_count == 1
        assert hook in bus.hooks

    def test_unregister_hook(self):
        """Test unregistering a hook."""
        bus = EventBus()
        hook = Mock()

        bus.register(hook)
        assert bus.hook_count == 1

        bus.unregister(hook)
        assert bus.hook_count == 0

    def test_emit_event_to_single_hook(self):
        """Test emitting an event to a single hook."""
        bus = EventBus()
        hook = Mock()
        hook.handle_event = Mock()

        bus.register(hook)

        event = BaseEvent(event_type="test", timestamp=datetime.utcnow(), metadata={})

        bus.emit(event)

        hook.handle_event.assert_called_once_with(event)
        assert bus.event_count == 1

    def test_emit_event_to_multiple_hooks(self):
        """Test emitting an event to multiple hooks."""
        bus = EventBus()
        hook1 = Mock()
        hook1.handle_event = Mock()
        hook2 = Mock()
        hook2.handle_event = Mock()

        bus.register(hook1)
        bus.register(hook2)

        event = BaseEvent(event_type="test", timestamp=datetime.utcnow(), metadata={})

        bus.emit(event)

        hook1.handle_event.assert_called_once_with(event)
        hook2.handle_event.assert_called_once_with(event)
        assert bus.event_count == 1

    def test_hook_failure_does_not_stop_other_hooks(self):
        """Test that a hook failure doesn't prevent other hooks from executing."""
        bus = EventBus()

        # Hook that raises an exception
        failing_hook = Mock()
        failing_hook.handle_event = Mock(side_effect=Exception("Hook failed"))

        # Hook that should still execute
        working_hook = Mock()
        working_hook.handle_event = Mock()

        bus.register(failing_hook)
        bus.register(working_hook)

        event = BaseEvent(event_type="test", timestamp=datetime.utcnow(), metadata={})

        # Should not raise exception
        bus.emit(event)

        # Both hooks should have been called
        failing_hook.handle_event.assert_called_once_with(event)
        working_hook.handle_event.assert_called_once_with(event)

    def test_clear_hooks(self):
        """Test clearing all hooks."""
        bus = EventBus()
        hook1 = Mock()
        hook2 = Mock()

        bus.register(hook1)
        bus.register(hook2)
        assert bus.hook_count == 2

        bus.clear_hooks()
        assert bus.hook_count == 0


class TestLoggingAlertHook:
    """Test LoggingAlertHook."""

    def test_logging_hook_creation(self):
        """Test creating a logging hook."""
        hook = LoggingAlertHook(log_level="INFO")
        assert hook.log_level == 20  # INFO level

    @patch("baselinr.events.builtin_hooks.logging.getLogger")
    def test_logging_hook_handles_event(self, mock_get_logger):
        """Test that logging hook logs the event."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        hook = LoggingAlertHook(log_level="INFO")

        event = DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="users",
            column="age",
            metric="mean",
            baseline_value=30.5,
            current_value=35.2,
            change_percent=15.4,
            drift_severity="medium",
            metadata={},
        )

        hook.handle_event(event)

        # Verify logger was called
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert "DataDriftDetected" in str(call_args)


class TestSQLEventHook:
    """Test SQLEventHook."""

    def test_sql_hook_creation(self):
        """Test creating a SQL event hook."""
        engine = create_engine("sqlite:///:memory:")
        hook = SQLEventHook(engine=engine, table_name="test_events")

        assert hook.engine == engine
        assert hook.table_name == "test_events"

    def test_sql_hook_persists_drift_event(self):
        """Test that SQL hook persists a drift event."""
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")

        # Create events table
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                CREATE TABLE test_events (
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
                )
            """
            )

        hook = SQLEventHook(engine=engine, table_name="test_events")

        event = DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="users",
            column="age",
            metric="mean",
            baseline_value=30.5,
            current_value=35.2,
            change_percent=15.4,
            drift_severity="medium",
            metadata={},
        )

        # Persist event
        hook.handle_event(event)

        # Verify event was persisted
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT * FROM test_events").fetchone()
            assert result is not None
            row = result._mapping
            assert row["event_type"] == "DataDriftDetected"
            assert row["table_name"] == "users"
            assert row["column_name"] == "age"
            assert row["metric_name"] == "mean"

    def test_sql_hook_persists_profiling_event(self):
        """Test that SQL hook persists a profiling event."""
        # Create in-memory database
        engine = create_engine("sqlite:///:memory:")

        # Create events table
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                CREATE TABLE test_events (
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
                )
            """
            )

        hook = SQLEventHook(engine=engine, table_name="test_events")

        event = ProfilingCompleted(
            event_type="ProfilingCompleted",
            timestamp=datetime.utcnow(),
            table="users",
            run_id="test-run-123",
            row_count=1000,
            column_count=10,
            duration_seconds=5.5,
            metadata={},
        )

        # Persist event
        hook.handle_event(event)

        # Verify event was persisted
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT * FROM test_events").fetchone()
            assert result is not None
            row = result._mapping
            assert row["event_type"] == "ProfilingCompleted"


class TestEventBusIntegration:
    """Integration tests for the event system."""

    def test_full_event_flow(self):
        """Test complete event flow from emission to multiple hooks."""
        # Setup
        bus = EventBus()

        # Create in-memory database for SQL hook
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                CREATE TABLE test_events (
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
                )
            """
            )

        # Register hooks
        logging_hook = LoggingAlertHook()
        sql_hook = SQLEventHook(engine=engine, table_name="test_events")

        bus.register(logging_hook)
        bus.register(sql_hook)

        # Emit event
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
            metadata={},
        )

        bus.emit(event)

        # Verify
        assert bus.event_count == 1

        # Check SQL persistence
        with engine.connect() as conn:
            result = conn.exec_driver_sql("SELECT * FROM test_events").fetchone()
            assert result is not None
            row = result._mapping
            assert row["event_type"] == "DataDriftDetected"
            assert row["drift_severity"] == "high"

    def test_slack_alert_hook_drift(self):
        """Test Slack alert hook with drift event."""
        from unittest.mock import MagicMock, Mock, patch

        # Mock requests module before importing SlackAlertHook
        mock_requests = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        with patch.dict("sys.modules", {"requests": mock_requests}):
            from baselinr.events import SlackAlertHook

            # Create hook
            hook = SlackAlertHook(
                webhook_url="https://hooks.slack.com/test",
                channel="#test",
                username="TestBot",
                min_severity="low",
            )

            # Create and emit drift event
            event = DataDriftDetected(
                event_type="DataDriftDetected",
                timestamp=datetime.utcnow(),
                table="orders",
                column="total_amount",
                metric="mean",
                baseline_value=100.0,
                current_value=150.0,
                change_percent=50.0,
                drift_severity="high",
                metadata={},
            )

            hook.handle_event(event)

            # Verify Slack was called
            assert mock_requests.post.called
            call_args = mock_requests.post.call_args
            assert call_args[0][0] == "https://hooks.slack.com/test"

            # Verify payload structure
            payload = call_args[1]["json"]
            assert payload["username"] == "TestBot"
            assert "Data Drift Detected" in payload["text"]
            assert len(payload["attachments"]) > 0
            assert payload["attachments"][0]["color"] == "#FF0000"  # Red for high severity

    def test_slack_alert_hook_severity_filter(self):
        """Test Slack alert hook filters by severity."""
        from unittest.mock import MagicMock, Mock, patch

        # Mock requests module before importing SlackAlertHook
        mock_requests = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        with patch.dict("sys.modules", {"requests": mock_requests}):
            from baselinr.events import SlackAlertHook

            # Create hook with high severity threshold
            hook = SlackAlertHook(
                webhook_url="https://hooks.slack.com/test",
                min_severity="high",  # Only high severity
            )

            # Create low severity event (should be filtered)
            event = DataDriftDetected(
                event_type="DataDriftDetected",
                timestamp=datetime.utcnow(),
                table="orders",
                column="total_amount",
                metric="mean",
                baseline_value=100.0,
                current_value=105.0,
                change_percent=5.0,
                drift_severity="low",
                metadata={},
            )

            hook.handle_event(event)

            # Verify Slack was NOT called (filtered by severity)
            assert not mock_requests.post.called

    def test_slack_alert_hook_schema_change(self):
        """Test Slack alert hook with schema change event."""
        from unittest.mock import MagicMock, Mock, patch

        # Mock requests module before importing SlackAlertHook
        mock_requests = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response

        with patch.dict("sys.modules", {"requests": mock_requests}):
            from baselinr.events import SlackAlertHook

            # Create hook
            hook = SlackAlertHook(webhook_url="https://hooks.slack.com/test", username="TestBot")

            # Create schema change event
            event = SchemaChangeDetected(
                event_type="SchemaChangeDetected",
                timestamp=datetime.utcnow(),
                table="users",
                change_type="column_added",
                column="email",
                metadata={},
            )

            hook.handle_event(event)

            # Verify Slack was called
            assert mock_requests.post.called
            payload = mock_requests.post.call_args[1]["json"]
            assert "Schema Change Detected" in payload["text"]

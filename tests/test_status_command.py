"""Tests for status CLI command."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text

from baselinr.cli import status_command
from baselinr.query import MetadataQueryClient


@pytest.fixture
def temp_db_engine():
    """Create temporary SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Create schema
    with engine.connect() as conn:
        conn.execute(
            text(
                """
            CREATE TABLE baselinr_runs (
                run_id VARCHAR(36),
                dataset_name VARCHAR(255),
                schema_name VARCHAR(255),
                profiled_at TIMESTAMP,
                environment VARCHAR(50),
                status VARCHAR(20),
                row_count INTEGER,
                column_count INTEGER,
                PRIMARY KEY (run_id, dataset_name)
            )
        """
            )
        )

        conn.execute(
            text(
                """
            CREATE TABLE baselinr_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id VARCHAR(36),
                dataset_name VARCHAR(255),
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                column_type VARCHAR(100),
                metric_name VARCHAR(100),
                metric_value TEXT,
                profiled_at TIMESTAMP
            )
        """
            )
        )

        conn.execute(
            text(
                """
            CREATE TABLE baselinr_events (
                event_id VARCHAR(36) PRIMARY KEY,
                event_type VARCHAR(100),
                run_id VARCHAR(36),
                table_name VARCHAR(255),
                column_name VARCHAR(255),
                metric_name VARCHAR(100),
                baseline_value FLOAT,
                current_value FLOAT,
                change_percent FLOAT,
                drift_severity VARCHAR(20),
                timestamp TIMESTAMP,
                metadata TEXT
            )
        """
            )
        )

        conn.commit()

    yield engine
    engine.dispose()


@pytest.fixture
def sample_status_data(temp_db_engine):
    """Create sample data for status command testing."""
    import json
    from datetime import datetime, timedelta

    with temp_db_engine.connect() as conn:
        now = datetime.utcnow()

        # Insert runs
        runs = [
            (
                "run-1",
                "customers",
                "public",
                now - timedelta(hours=1),
                "production",
                "completed",
                1000,
                10,
            ),
            (
                "run-2",
                "orders",
                "public",
                now - timedelta(hours=2),
                "production",
                "completed",
                5000,
                15,
            ),
        ]

        for run in runs:
            conn.execute(
                text(
                    """
                INSERT INTO baselinr_runs
                (run_id, dataset_name, schema_name, profiled_at, environment, status, row_count, column_count)
                VALUES (:run_id, :dataset_name, :schema_name, :profiled_at, :environment, :status, :row_count, :column_count)
            """
                ),
                {
                    "run_id": run[0],
                    "dataset_name": run[1],
                    "schema_name": run[2],
                    "profiled_at": run[3],
                    "environment": run[4],
                    "status": run[5],
                    "row_count": run[6],
                    "column_count": run[7],
                },
            )

        # Insert events
        events = [
            (
                "event-1",
                "ProfilingCompleted",
                "run-1",
                "customers",
                None,
                None,
                None,
                None,
                None,
                None,
                now - timedelta(hours=1),
                json.dumps({"duration_seconds": 45.5, "row_count": 1000, "column_count": 10}),
            ),
            (
                "event-2",
                "AnomalyDetected",
                "run-1",
                "customers",
                "email",
                "null_ratio",
                None,
                None,
                None,
                "medium",
                now - timedelta(hours=1),
                json.dumps({"anomaly_type": "outlier"}),
            ),
            (
                "event-3",
                "ProfilingCompleted",
                "run-2",
                "orders",
                None,
                None,
                None,
                None,
                None,
                None,
                now - timedelta(hours=2),
                json.dumps({"duration_seconds": 120.0, "row_count": 5000, "column_count": 15}),
            ),
        ]

        for event in events:
            conn.execute(
                text(
                    """
                INSERT INTO baselinr_events
                (event_id, event_type, run_id, table_name, column_name, metric_name, baseline_value, current_value, change_percent, drift_severity, timestamp, metadata)
                VALUES (:event_id, :event_type, :run_id, :table_name, :column_name, :metric_name, :baseline_value, :current_value, :change_percent, :drift_severity, :timestamp, :metadata)
            """
                ),
                {
                    "event_id": event[0],
                    "event_type": event[1],
                    "run_id": event[2],
                    "table_name": event[3],
                    "column_name": event[4],
                    "metric_name": event[5],
                    "baseline_value": event[6],
                    "current_value": event[7],
                    "change_percent": event[8],
                    "drift_severity": event[9],
                    "timestamp": event[10],
                    "metadata": event[11],
                },
            )

        # Insert results (metrics)
        results = [
            ("run-1", "customers", "public", "email", "VARCHAR", "null_count", "10", now),
            ("run-1", "customers", "public", "email", "VARCHAR", "null_percent", "1.0", now),
            ("run-1", "customers", "public", "age", "INTEGER", "mean", "35.2", now),
            ("run-2", "orders", "public", "total", "DECIMAL", "mean", "100.5", now),
            ("run-2", "orders", "public", "total", "DECIMAL", "stddev", "25.3", now),
        ]

        for result in results:
            conn.execute(
                text(
                    """
                INSERT INTO baselinr_results
                (run_id, dataset_name, schema_name, column_name, column_type, metric_name, metric_value, profiled_at)
                VALUES (:run_id, :dataset_name, :schema_name, :column_name, :column_type, :metric_name, :metric_value, :profiled_at)
            """
                ),
                {
                    "run_id": result[0],
                    "dataset_name": result[1],
                    "schema_name": result[2],
                    "column_name": result[3],
                    "column_type": result[4],
                    "metric_name": result[5],
                    "metric_value": result[6],
                    "profiled_at": result[7],
                },
            )

        # Insert drift events
        drift_events = [
            (
                "drift-1",
                "drift_detected",
                None,
                "customers",
                "email",
                "null_percent",
                1.0,
                2.5,
                150.0,
                "high",
                now - timedelta(hours=1),
                None,
            ),
        ]

        for event in drift_events:
            conn.execute(
                text(
                    """
                INSERT INTO baselinr_events
                (event_id, event_type, run_id, table_name, column_name, metric_name, baseline_value, current_value, change_percent, drift_severity, timestamp, metadata)
                VALUES (:event_id, :event_type, :run_id, :table_name, :column_name, :metric_name, :baseline_value, :current_value, :change_percent, :drift_severity, :timestamp, :metadata)
            """
                ),
                {
                    "event_id": event[0],
                    "event_type": event[1],
                    "run_id": event[2],
                    "table_name": event[3],
                    "column_name": event[4],
                    "metric_name": event[5],
                    "baseline_value": event[6],
                    "current_value": event[7],
                    "change_percent": event[8],
                    "drift_severity": event[9],
                    "timestamp": event[10],
                    "metadata": event[11],
                },
            )

        conn.commit()


@pytest.fixture
def mock_config():
    """Create mock config for testing."""
    config = MagicMock()
    config.storage.runs_table = "baselinr_runs"
    config.storage.results_table = "baselinr_results"
    config.storage.connection.type = "sqlite"
    config.retry = None
    return config


def test_status_command_basic(temp_db_engine, sample_status_data, mock_config, tmp_path):
    """Test basic status command execution."""
    # Create a temporary config file
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    # Mock the config loader and connector
    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=mock_config):
        with patch("baselinr.connectors.factory.create_connector") as mock_connector:
            mock_connector_instance = MagicMock()
            mock_connector_instance.engine = temp_db_engine
            mock_connector.return_value = mock_connector_instance

            args = MagicMock()
            args.config = str(config_file)
            args.drift_only = False
            args.limit = 20
            args.days = 7
            args.json = False
            args.watch = None

            # Should not raise
            result = status_command(args)
            assert result == 0


def test_status_command_json_output(temp_db_engine, sample_status_data, mock_config, tmp_path, capsys):
    """Test status command with JSON output."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=mock_config):
        with patch("baselinr.connectors.factory.create_connector") as mock_connector:
            mock_connector_instance = MagicMock()
            mock_connector_instance.engine = temp_db_engine
            mock_connector.return_value = mock_connector_instance

            args = MagicMock()
            args.config = str(config_file)
            args.drift_only = False
            args.limit = 20
            args.days = 7
            args.json = True
            args.watch = None

            result = status_command(args)
            assert result == 0

            # Check output is valid JSON
            captured = capsys.readouterr()
            output = captured.out
            parsed = json.loads(output)
            assert "runs" in parsed
            assert "drift_summary" in parsed


def test_status_command_drift_only(temp_db_engine, sample_status_data, mock_config, tmp_path, capsys):
    """Test status command with drift-only flag."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=mock_config):
        with patch("baselinr.connectors.factory.create_connector") as mock_connector:
            mock_connector_instance = MagicMock()
            mock_connector_instance.engine = temp_db_engine
            mock_connector.return_value = mock_connector_instance

            args = MagicMock()
            args.config = str(config_file)
            args.drift_only = True
            args.limit = 20
            args.days = 7
            args.json = True
            args.watch = None

            result = status_command(args)
            assert result == 0

            captured = capsys.readouterr()
            output = captured.out
            parsed = json.loads(output)
            # With drift_only, runs should be empty or not present
            assert "drift_summary" in parsed


def test_status_command_limit(temp_db_engine, sample_status_data, mock_config, tmp_path, capsys):
    """Test status command with limit."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=mock_config):
        with patch("baselinr.connectors.factory.create_connector") as mock_connector:
            mock_connector_instance = MagicMock()
            mock_connector_instance.engine = temp_db_engine
            mock_connector.return_value = mock_connector_instance

            args = MagicMock()
            args.config = str(config_file)
            args.drift_only = False
            args.limit = 1
            args.days = 7
            args.json = True
            args.watch = None

            result = status_command(args)
            assert result == 0

            captured = capsys.readouterr()
            output = captured.out
            parsed = json.loads(output)
            assert len(parsed["runs"]) <= 1


def test_status_command_empty_database(temp_db_engine, mock_config, tmp_path):
    """Test status command with empty database."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=mock_config):
        with patch("baselinr.connectors.factory.create_connector") as mock_connector:
            mock_connector_instance = MagicMock()
            mock_connector_instance.engine = temp_db_engine
            mock_connector.return_value = mock_connector_instance

            args = MagicMock()
            args.config = str(config_file)
            args.drift_only = False
            args.limit = 20
            args.days = 7
            args.json = True
            args.watch = None

            result = status_command(args)
            assert result == 0  # Should handle empty gracefully


def test_status_command_error_handling(tmp_path):
    """Test status command error handling."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", side_effect=Exception("Config error")):
        args = MagicMock()
        args.config = str(config_file)
        args.drift_only = False
        args.limit = 20
        args.days = 7
        args.json = False
        args.watch = None

        result = status_command(args)
        assert result == 1  # Should return error code


def test_status_command_watch_mode_skipped(temp_db_engine, sample_status_data, mock_config, tmp_path):
    """Test that watch mode is skipped when not requested."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("environment: test\n")

    with patch("baselinr.cli.ConfigLoader.load_from_file", return_value=mock_config):
        with patch("baselinr.connectors.factory.create_connector") as mock_connector:
            mock_connector_instance = MagicMock()
            mock_connector_instance.engine = temp_db_engine
            mock_connector.return_value = mock_connector_instance

            args = MagicMock()
            args.config = str(config_file)
            args.drift_only = False
            args.limit = 20
            args.days = 7
            args.json = False
            args.watch = None  # No watch mode

            # Should not call watch mode
            with patch("baselinr.cli._status_watch_mode") as mock_watch:
                result = status_command(args)
                assert result == 0
                mock_watch.assert_not_called()


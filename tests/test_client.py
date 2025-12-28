"""Tests for Baselinr Python SDK client."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from baselinr import BaselinrClient
from baselinr.config.schema import BaselinrConfig, ConnectionConfig, DatabaseType, StorageConfig


@pytest.fixture
def sample_config():
    """Create a sample BaselinrConfig for testing."""
    return BaselinrConfig(
        environment="test",
        source=ConnectionConfig(
            type=DatabaseType.SQLITE,
            database=":memory:",
            filepath=":memory:",
        ),
        storage=StorageConfig(
            connection=ConnectionConfig(
                type=DatabaseType.SQLITE,
                database=":memory:",
                filepath=":memory:",
            ),
            runs_table="baselinr_runs",
            results_table="baselinr_results",
            create_tables=True,
        ),
    )


@pytest.fixture
def config_file(tmp_path, sample_config):
    """Create a temporary config file."""
    import yaml

    config_dict = {
        "environment": sample_config.environment,
        "source": {
            "type": sample_config.source.type,
            "database": sample_config.source.database,
            "filepath": sample_config.source.filepath,
        },
        "storage": {
            "connection": {
                "type": sample_config.storage.connection.type,
                "database": sample_config.storage.connection.database,
                "filepath": sample_config.storage.connection.filepath,
            },
            "runs_table": sample_config.storage.runs_table,
            "results_table": sample_config.storage.results_table,
            "create_tables": sample_config.storage.create_tables,
        },
    }

    config_path = tmp_path / "config.yml"
    with open(config_path, "w") as f:
        yaml.dump(config_dict, f)

    return str(config_path)


def test_client_init_with_config_path(config_file):
    """Test initializing client with config path."""
    client = BaselinrClient(config_path=config_file)
    assert client.config.environment == "test"
    assert client.config.source.type == "sqlite"


def test_client_init_with_config_object(sample_config):
    """Test initializing client with config object."""
    client = BaselinrClient(config=sample_config)
    assert client.config.environment == "test"
    assert client.config is sample_config


def test_client_init_with_config_dict(sample_config):
    """Test initializing client with config dictionary."""
    config_dict = {
        "environment": sample_config.environment,
        "source": {
            "type": sample_config.source.type,
            "database": sample_config.source.database,
            "filepath": sample_config.source.filepath,
        },
        "storage": {
            "connection": {
                "type": sample_config.storage.connection.type,
                "database": sample_config.storage.connection.database,
                "filepath": sample_config.storage.connection.filepath,
            },
            "runs_table": sample_config.storage.runs_table,
            "results_table": sample_config.storage.results_table,
            "create_tables": sample_config.storage.create_tables,
        },
    }

    client = BaselinrClient(config=config_dict)
    assert client.config.environment == "test"


def test_client_init_raises_on_both_config_and_path(sample_config):
    """Test that client raises error when both config and path are provided."""
    with pytest.raises(ValueError, match="Provide either config_path or config"):
        BaselinrClient(config_path="config.yml", config=sample_config)


def test_client_init_raises_on_neither_config():
    """Test that client raises error when neither config nor path are provided."""
    with pytest.raises(ValueError, match="Provide either config_path or config"):
        BaselinrClient()


def test_client_plan(sample_config):
    """Test plan method."""
    client = BaselinrClient(config=sample_config)

    with patch("baselinr.planner.PlanBuilder") as mock_builder:
        mock_plan = Mock()
        mock_plan.total_tables = 2
        mock_plan.estimated_metrics = 100
        mock_builder.return_value.build_plan.return_value = mock_plan

        plan = client.plan()
        assert plan.total_tables == 2
        assert plan.estimated_metrics == 100
        mock_builder.assert_called_once_with(sample_config, config_file_path=None)


def test_client_profile(sample_config):
    """Test profile method."""
    client = BaselinrClient(config=sample_config)

    with patch("baselinr.profiling.core.ProfileEngine") as mock_engine_class, patch(
        "baselinr.storage.writer.ResultWriter"
    ) as mock_writer_class, patch("baselinr.cli.create_event_bus") as mock_event_bus:
        mock_engine = Mock()
        mock_engine.profile.return_value = []
        mock_engine_class.return_value = mock_engine

        mock_writer = Mock()
        mock_writer_class.return_value = mock_writer

        mock_event_bus.return_value = None

        results = client.profile(dry_run=True)
        assert results == []

        # Verify engine was created
        mock_engine_class.assert_called_once()
        # Verify profile was called
        mock_engine.profile.assert_called_once()

        # In dry_run mode, writer should not be created
        mock_writer_class.assert_not_called()


def test_client_detect_drift(sample_config):
    """Test detect_drift method."""
    client = BaselinrClient(config=sample_config)

    with patch("baselinr.drift.detector.DriftDetector") as mock_detector_class, patch(
        "baselinr.cli.create_event_bus"
    ) as mock_event_bus:
        mock_detector = Mock()
        mock_report = Mock()
        mock_report.column_drifts = []
        mock_report.schema_changes = []
        mock_detector.detect_drift.return_value = mock_report
        mock_detector_class.return_value = mock_detector

        mock_event_bus.return_value = None

        report = client.detect_drift("test_table")
        assert report == mock_report

        mock_detector.detect_drift.assert_called_once_with(
            dataset_name="test_table",
            baseline_run_id=None,
            current_run_id=None,
            schema_name=None,
        )


def test_client_query_runs(sample_config):
    """Test query_runs method."""
    client = BaselinrClient(config=sample_config)

    mock_query_client = Mock()
    mock_run = Mock()
    mock_run.run_id = "test-run-id"
    mock_query_client.query_runs.return_value = [mock_run]

    with patch.object(client, "_ensure_query_client", return_value=mock_query_client):
        runs = client.query_runs(days=7, limit=10)
        assert len(runs) == 1
        assert runs[0].run_id == "test-run-id"

        mock_query_client.query_runs.assert_called_once_with(
            schema=None,
            table=None,
            status=None,
            environment=None,
            days=7,
            limit=10,
            offset=0,
        )


def test_client_query_drift(sample_config):
    """Test query_drift method."""
    client = BaselinrClient(config=sample_config)

    mock_query_client = Mock()
    mock_drift_event = Mock()
    mock_query_client.query_drift_events.return_value = [mock_drift_event]

    with patch.object(client, "_ensure_query_client", return_value=mock_query_client):
        drift_events = client.query_drift(table="test_table", severity="high", days=7)
        assert len(drift_events) == 1

        mock_query_client.query_drift_events.assert_called_once_with(
            table="test_table",
            severity="high",
            days=7,
            limit=100,
            offset=0,
        )


def test_client_query_anomalies_with_run_id(sample_config):
    """Test query_anomalies method with run_id."""
    client = BaselinrClient(config=sample_config)

    mock_query_client = Mock()
    mock_query_client.query_run_events.return_value = [
        {
            "event_type": "AnomalyDetected",
            "table_name": "test_table",
            "column_name": "test_column",
        }
    ]

    with patch.object(client, "_ensure_query_client", return_value=mock_query_client):
        anomalies = client.query_anomalies(run_id="test-run-id")
        assert len(anomalies) == 1
        assert anomalies[0]["event_type"] == "AnomalyDetected"

        mock_query_client.query_run_events.assert_called_once_with(
            "test-run-id", event_types=["AnomalyDetected"]
        )


def test_client_query_run_details(sample_config):
    """Test query_run_details method."""
    client = BaselinrClient(config=sample_config)

    mock_query_client = Mock()
    mock_details = {"run": {"run_id": "test-run-id"}}
    mock_query_client.query_run_details.return_value = mock_details

    with patch.object(client, "_ensure_query_client", return_value=mock_query_client):
        details = client.query_run_details("test-run-id")
        assert details == mock_details

        mock_query_client.query_run_details.assert_called_once_with(
            "test-run-id", dataset_name=None
        )


def test_client_query_table_history(sample_config):
    """Test query_table_history method."""
    client = BaselinrClient(config=sample_config)

    mock_query_client = Mock()
    mock_history = {"table_name": "test_table", "run_count": 5}
    mock_query_client.query_table_history.return_value = mock_history

    with patch.object(client, "_ensure_query_client", return_value=mock_query_client):
        history = client.query_table_history("test_table", days=30)
        assert history == mock_history

        mock_query_client.query_table_history.assert_called_once_with(
            table_name="test_table", schema_name=None, days=30
        )


def test_client_get_status(sample_config):
    """Test get_status method."""
    client = BaselinrClient(config=sample_config)

    mock_query_client = Mock()
    mock_run = Mock()
    mock_run.run_id = "test-run-id"
    mock_run.dataset_name = "test_table"
    mock_run.schema_name = None
    mock_run.profiled_at = "2024-01-01T00:00:00"
    mock_run.row_count = 100
    mock_query_client.query_runs.return_value = [mock_run]
    mock_query_client.query_run_events.return_value = []
    mock_query_client.query_drift_events.return_value = []
    mock_query_client.query_active_drift_summary.return_value = []
    mock_query_client.engine = Mock()
    mock_query_client.results_table = "baselinr_results"

    with patch.object(client, "_ensure_query_client", return_value=mock_query_client):
        status = client.get_status(days=7, limit=10)

        assert "timestamp" in status
        assert "drift_summary" in status
        assert "runs_data" in status
        assert len(status["runs_data"]) == 1


def test_client_migrate_status(sample_config):
    """Test migrate_status method."""
    client = BaselinrClient(config=sample_config)

    mock_manager = Mock()
    mock_manager.get_current_version.return_value = 1

    with patch.object(client, "_ensure_migration_manager", return_value=mock_manager):
        status = client.migrate_status()

        assert "current_version" in status
        assert "latest_version" in status
        assert "pending_migrations" in status
        assert "migration_count" in status


def test_client_migrate_apply(sample_config):
    """Test migrate_apply method."""
    client = BaselinrClient(config=sample_config)

    mock_manager = Mock()
    mock_manager.migrate_to.return_value = True

    with patch.object(client, "_ensure_migration_manager", return_value=mock_manager):
        result = client.migrate_apply(target_version=1, dry_run=False)

        assert "target_version" in result
        assert result["success"] is True
        mock_manager.migrate_to.assert_called_once_with(1, dry_run=False)


def test_client_migrate_apply_dry_run(sample_config):
    """Test migrate_apply method with dry_run=True."""
    client = BaselinrClient(config=sample_config)

    mock_manager = Mock()
    mock_manager.get_current_version.return_value = 0

    mock_migration1 = Mock()
    mock_migration1.version = 1
    mock_migration2 = Mock()
    mock_migration2.version = 2

    with patch.object(client, "_ensure_migration_manager", return_value=mock_manager):
        # Patch the imports inside the method
        with patch("baselinr.storage.migrations.versions.ALL_MIGRATIONS", [mock_migration1, mock_migration2]):
            with patch("baselinr.storage.schema_version.CURRENT_SCHEMA_VERSION", 2):
                result = client.migrate_apply(target_version=2, dry_run=True)

                assert "target_version" in result
                assert result["preview"] is True
                assert "migrations_to_apply" in result
                # In dry_run mode, migrate_to should not be called
                mock_manager.migrate_to.assert_not_called()


def test_client_migrate_validate(sample_config):
    """Test migrate_validate method."""
    client = BaselinrClient(config=sample_config)

    mock_manager = Mock()
    mock_manager.validate_schema.return_value = {
        "valid": True,
        "version": 1,
        "errors": [],
        "warnings": [],
    }

    with patch.object(client, "_ensure_migration_manager", return_value=mock_manager):
        result = client.migrate_validate()

        assert "is_valid" in result
        assert result["is_valid"] is True
        assert "version" in result
        mock_manager.validate_schema.assert_called_once()


def test_client_config_property(sample_config):
    """Test config property returns cached config."""
    client = BaselinrClient(config=sample_config)
    assert client.config is sample_config
    assert client.config.environment == "test"


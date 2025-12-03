"""
Tests for Airflow integration.

Tests operators and RCA collector with mocked Airflow dependencies.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Skip entire test module if Airflow is not available
try:
    from baselinr.integrations.airflow import (
        BaselinrDriftOperator,
        BaselinrProfileOperator,
        BaselinrQueryOperator,
    )
    from baselinr.rca.collectors.airflow_run_collector import AirflowRunCollector

    AIRFLOW_TESTS_AVAILABLE = True
except (ImportError, Exception) as e:
    AIRFLOW_TESTS_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason=f"Airflow integration not available: {e}")


def _write_config(path: Path, tables) -> Path:
    """Write a test configuration file."""
    config = {
        "environment": "test",
        "source": {
            "type": "sqlite",
            "database": "source.db",
            "filepath": str(path.parent / "source.db"),
        },
        "storage": {
            "connection": {
                "type": "sqlite",
                "database": "results.db",
                "filepath": str(path.parent / "results.db"),
            },
            "results_table": "baselinr_results",
            "runs_table": "baselinr_runs",
        },
        "profiling": {
            "tables": [{"schema": "public", "table": table} for table in tables],
            "metrics": ["count", "null_count"],
            "compute_histograms": False,
        },
    }
    path.write_text(yaml.safe_dump(config))
    return path


@pytest.fixture
def mock_airflow_context():
    """Create a mock Airflow context."""
    context = {
        "ti": MagicMock(),
        "dag": MagicMock(),
        "ds": "2024-01-01",
        "ts": "2024-01-01T00:00:00",
    }
    context["ti"].xcom_push = MagicMock()
    return context


class TestBaselinrProfileOperator:
    """Tests for BaselinrProfileOperator."""

    def test_operator_initialization_with_config_path(self, tmp_path):
        """Test operator initialization with config_path."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        config_path = _write_config(tmp_path / "config.yml", ["users"])

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            operator = BaselinrProfileOperator(
                task_id="test_profile",
                config_path=str(config_path),
            )

            assert operator.config_path == str(config_path)
            assert operator.config is None
            assert operator.dry_run is False

    def test_operator_initialization_with_config_dict(self, tmp_path):
        """Test operator initialization with config dict."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        config = {
            "environment": "test",
            "source": {"type": "sqlite", "filepath": str(tmp_path / "source.db")},
            "storage": {
                "connection": {"type": "sqlite", "filepath": str(tmp_path / "results.db")}
            },
        }

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            operator = BaselinrProfileOperator(
                task_id="test_profile",
                config=config,
            )

            assert operator.config_path is None
            assert operator.config == config

    def test_operator_initialization_validation(self):
        """Test operator initialization validation."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            # Both config_path and config provided
            with pytest.raises(ValueError, match="Provide either config_path or config"):
                BaselinrProfileOperator(
                    task_id="test",
                    config_path="/path/to/config.yml",
                    config={"source": {}},
                )

            # Neither provided
            with pytest.raises(ValueError, match="Provide either config_path or config"):
                BaselinrProfileOperator(task_id="test")

    @patch("baselinr.BaselinrClient")
    def test_operator_execution(self, mock_client_class, tmp_path, mock_airflow_context):
        """Test operator execution."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        config_path = _write_config(tmp_path / "config.yml", ["users"])

        # Mock client and results
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.run_id = "test-run-123"
        mock_result.dataset_name = "users"
        mock_client.profile.return_value = [mock_result]
        mock_client_class.return_value = mock_client

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            operator = BaselinrProfileOperator(
                task_id="test_profile",
                config_path=str(config_path),
            )

            # Execute the callable
            result = operator.python_callable(**mock_airflow_context)

            # Verify results
            assert result["tables_count"] == 1
            assert "users" in result["tables_profiled"]
            assert "test-run-123" in result["run_ids"]
            mock_client.profile.assert_called_once()


class TestBaselinrDriftOperator:
    """Tests for BaselinrDriftOperator."""

    def test_operator_initialization(self, tmp_path):
        """Test operator initialization."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        config_path = _write_config(tmp_path / "config.yml", ["users"])

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            operator = BaselinrDriftOperator(
                task_id="test_drift",
                config_path=str(config_path),
                dataset_name="customers",
                fail_on_drift=False,
            )

            assert operator.dataset_name == "customers"
            assert operator.fail_on_drift is False

    def test_operator_requires_dataset_name(self):
        """Test that dataset_name is required."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            with pytest.raises(ValueError, match="dataset_name is required"):
                BaselinrDriftOperator(
                    task_id="test",
                    config_path="/path/to/config.yml",
                    dataset_name="",  # Empty string
                )

    @patch("baselinr.BaselinrClient")
    def test_operator_execution_no_drift(self, mock_client_class, tmp_path, mock_airflow_context):
        """Test operator execution with no drift."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        config_path = _write_config(tmp_path / "config.yml", ["users"])

        # Mock drift report with no drift
        mock_client = MagicMock()
        mock_report = MagicMock()
        mock_report.column_drifts = []
        mock_report.schema_changes = []
        mock_report.to_dict.return_value = {}
        mock_client.detect_drift.return_value = mock_report
        mock_client_class.return_value = mock_client

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            operator = BaselinrDriftOperator(
                task_id="test_drift",
                config_path=str(config_path),
                dataset_name="customers",
                fail_on_drift=False,
            )

            result = operator.python_callable(**mock_airflow_context)

            assert result["has_drift"] is False
            assert result["column_drifts_count"] == 0

    @patch("baselinr.BaselinrClient")
    def test_operator_execution_with_drift_fail(self, mock_client_class, tmp_path, mock_airflow_context):
        """Test operator execution with drift and fail_on_drift=True."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        config_path = _write_config(tmp_path / "config.yml", ["users"])

        # Mock drift report with drift
        mock_client = MagicMock()
        mock_report = MagicMock()
        mock_drift = MagicMock()
        mock_drift.severity = "high"
        mock_report.column_drifts = [mock_drift]
        mock_report.schema_changes = []
        mock_report.to_dict.return_value = {}
        mock_client.detect_drift.return_value = mock_report
        mock_client_class.return_value = mock_client

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            operator = BaselinrDriftOperator(
                task_id="test_drift",
                config_path=str(config_path),
                dataset_name="customers",
                fail_on_drift=True,
            )

            with pytest.raises(ValueError, match="Drift detected"):
                operator.python_callable(**mock_airflow_context)


class TestBaselinrQueryOperator:
    """Tests for BaselinrQueryOperator."""

    def test_operator_initialization(self, tmp_path):
        """Test operator initialization."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        config_path = _write_config(tmp_path / "config.yml", ["users"])

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            operator = BaselinrQueryOperator(
                task_id="test_query",
                config_path=str(config_path),
                query_type="runs",
                days=7,
            )

            assert operator.query_type == "runs"
            assert operator.query_kwargs["days"] == 7

    def test_operator_invalid_query_type(self):
        """Test operator with invalid query_type."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            with pytest.raises(ValueError, match="query_type must be one of"):
                BaselinrQueryOperator(
                    task_id="test",
                    config_path="/path/to/config.yml",
                    query_type="invalid_type",
                )

    @patch("baselinr.BaselinrClient")
    def test_operator_execution_runs_query(self, mock_client_class, tmp_path, mock_airflow_context):
        """Test operator execution with runs query."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        config_path = _write_config(tmp_path / "config.yml", ["users"])

        # Mock query results
        mock_client = MagicMock()
        mock_run = MagicMock()
        mock_run.to_dict.return_value = {"run_id": "test-run", "table": "users"}
        mock_client.query_runs.return_value = [mock_run]
        mock_client_class.return_value = mock_client

        with patch("baselinr.integrations.airflow.operators.AIRFLOW_AVAILABLE", True):
            operator = BaselinrQueryOperator(
                task_id="test_query",
                config_path=str(config_path),
                query_type="runs",
                days=7,
            )

            result = operator.python_callable(**mock_airflow_context)

            assert len(result) == 1
            assert result[0]["run_id"] == "test-run"
            mock_client.query_runs.assert_called_once_with(days=7)


class TestAirflowRunCollector:
    """Tests for AirflowRunCollector."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock SQLAlchemy engine."""
        return MagicMock()

    def test_collector_initialization(self, mock_engine):
        """Test collector initialization."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        collector = AirflowRunCollector(
            engine=mock_engine,
            api_url="http://localhost:8080/api/v1",
            api_version="v1",
        )

        assert collector.api_url == "http://localhost:8080/api/v1"
        assert collector.api_version == "v1"

    def test_collector_from_env_vars(self, mock_engine, monkeypatch):
        """Test collector initialization from environment variables."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        monkeypatch.setenv("AIRFLOW_API_URL", "http://airflow:8080/api/v1")
        monkeypatch.setenv("AIRFLOW_API_VERSION", "v2")

        collector = AirflowRunCollector(engine=mock_engine)

        assert collector.api_url == "http://airflow:8080/api/v1"
        assert collector.api_version == "v2"

    def test_collect_from_api(self, mock_engine):
        """Test collection from REST API."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        collector = AirflowRunCollector(
            engine=mock_engine,
            api_url="http://localhost:8080/api/v1",
            api_version="v1",
        )

        # Mock requests module in sys.modules to avoid ImportError when requests is not installed
        # This allows the import inside _collect_from_api to work
        mock_requests_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "dag_runs": [
                {
                    "dag_id": "test_dag",
                    "dag_run_id": "test_run_123",
                    "state": "success",
                    "execution_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-01T00:05:00Z",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests_module.get.return_value = mock_response

        # Patch requests in sys.modules so the import inside _collect_from_api works
        with patch.dict(sys.modules, {"requests": mock_requests_module}):
            runs = collector._collect_from_api()

            assert len(runs) == 1
            assert runs[0].pipeline_name == "test_dag"
            assert runs[0].pipeline_type == "airflow"
            assert runs[0].status == "success"

    def test_collect_from_env(self, mock_engine, monkeypatch):
        """Test collection from environment variables."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        monkeypatch.setenv("AIRFLOW_CTX_DAG_ID", "test_dag")
        monkeypatch.setenv("AIRFLOW_CTX_RUN_ID", "test_run_123")
        monkeypatch.setenv("AIRFLOW_CTX_EXECUTION_DATE", "2024-01-01T00:00:00Z")

        collector = AirflowRunCollector(engine=mock_engine)

        run = collector._collect_from_env()

        assert run is not None
        assert run.pipeline_name == "test_dag"
        assert run.pipeline_type == "airflow"
        assert run.status == "running"

    def test_convert_api_run(self, mock_engine):
        """Test conversion of API run data to PipelineRun."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        collector = AirflowRunCollector(engine=mock_engine)

        dag_run_data = {
            "dag_id": "test_dag",
            "dag_run_id": "test_run_123",
            "state": "success",
            "execution_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-01T00:05:00Z",
        }

        pipeline_run = collector._convert_api_run(dag_run_data)

        assert pipeline_run is not None
        assert pipeline_run.pipeline_name == "test_dag"
        assert pipeline_run.run_id == "airflow_test_run_123"
        assert pipeline_run.status == "success"
        assert pipeline_run.duration_seconds == 300.0  # 5 minutes

    def test_status_mapping(self, mock_engine):
        """Test Airflow state to status mapping."""
        if not AIRFLOW_TESTS_AVAILABLE:
            pytest.skip("Airflow integration not available")

        collector = AirflowRunCollector(engine=mock_engine)

        test_cases = [
            ("success", "success"),
            ("failed", "failed"),
            ("running", "running"),
            ("queued", "running"),
            ("up_for_retry", "running"),
        ]

        for airflow_state, expected_status in test_cases:
            dag_run_data = {
                "dag_id": "test_dag",
                "dag_run_id": "test_run",
                "state": airflow_state,
                "execution_date": "2024-01-01T00:00:00Z",
            }

            pipeline_run = collector._convert_api_run(dag_run_data)
            assert pipeline_run.status == expected_status, f"Failed for state: {airflow_state}"


"""Tests for Airflow integration."""

import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from profilemesh.profiling.core import ProfilingResult


def _write_config(path: Path, tables) -> Path:
    """Helper to write a test config file."""
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
            "results_table": "profilemesh_results",
            "runs_table": "profilemesh_runs",
        },
        "profiling": {
            "tables": [{"schema": "public", "table": table} for table in tables],
            "metrics": ["count", "null_count"],
            "compute_histograms": False,
        },
    }
    path.write_text(yaml.safe_dump(config))
    return path


def _fake_result(table_name):
    """Create a fake profiling result for testing."""
    result = ProfilingResult(
        run_id="fake-run",
        dataset_name=table_name,
        schema_name="public",
        profiled_at=datetime.utcnow(),
    )
    result.columns = [{"column_name": "id", "metrics": {"count": 10}}]
    result.metadata = {"row_count": 10}
    return result


def test_hook_loads_config(tmp_path):
    """Test that ProfileMeshHook loads configuration."""
    airflow = pytest.importorskip("airflow")
    from profilemesh.integrations.airflow import ProfileMeshHook

    config_path = _write_config(tmp_path / "config.yml", ["users"])

    hook = ProfileMeshHook(config_path=str(config_path))
    config = hook.get_config()

    assert config.environment == "test"
    assert len(config.profiling.tables) == 1
    assert config.profiling.tables[0].table == "users"


def test_hook_builds_plan(tmp_path):
    """Test that ProfileMeshHook can build a profiling plan."""
    airflow = pytest.importorskip("airflow")
    from profilemesh.integrations.airflow import ProfileMeshHook

    config_path = _write_config(tmp_path / "config.yml", ["users", "events"])

    hook = ProfileMeshHook(config_path=str(config_path))
    plan = hook.build_plan()

    assert plan.total_tables == 2
    assert len(plan.tables) == 2


def test_operator_executes_profiling(tmp_path, monkeypatch):
    """Test that ProfileMeshProfilingOperator executes profiling."""
    airflow = pytest.importorskip("airflow")
    from airflow.models import TaskInstance
    from profilemesh.integrations.airflow import ProfileMeshProfilingOperator

    config_path = _write_config(tmp_path / "config.yml", ["users"])

    def fake_profile(self, table_patterns):
        return [_fake_result(table_patterns[0].table)]

    class DummyWriter:
        def __init__(self, *_args, **_kwargs):
            self.closed = False

        def write_results(self, *_args, **_kwargs):
            return None

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        "profilemesh.integrations.airflow.operators.ProfileEngine.profile",
        fake_profile,
    )
    monkeypatch.setattr(
        "profilemesh.integrations.airflow.operators.ResultWriter",
        DummyWriter,
    )

    operator = ProfileMeshProfilingOperator(
        task_id="test_profiling",
        config_path=str(config_path),
    )

    # Create mock context
    class MockTI:
        def __init__(self):
            self.task_id = "test_profiling"
            self.xcom_data = {}

        def xcom_push(self, key, value):
            self.xcom_data[key] = value

        def xcom_pull(self, task_ids, key, default=None):
            return self.xcom_data.get(key, default)

    mock_ti = MockTI()
    context = {"ti": mock_ti, "execution_date": datetime.utcnow()}

    result = operator.execute(context)

    assert result["environment"] == "test"
    assert result["tables_profiled"] == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["dataset_name"] == "users"

    # Check XCom was populated
    assert "profiling_results" in mock_ti.xcom_data


def test_table_operator_profiles_single_table(tmp_path, monkeypatch):
    """Test that ProfileMeshTableOperator profiles a single table."""
    airflow = pytest.importorskip("airflow")
    from profilemesh.integrations.airflow import ProfileMeshTableOperator

    config_path = _write_config(tmp_path / "config.yml", ["users"])

    def fake_profile(self, table_patterns):
        return [_fake_result(table_patterns[0].table)]

    class DummyWriter:
        def __init__(self, *_args, **_kwargs):
            pass

        def write_results(self, *_args, **_kwargs):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        "profilemesh.integrations.airflow.operators.ProfileEngine.profile",
        fake_profile,
    )
    monkeypatch.setattr(
        "profilemesh.integrations.airflow.operators.ResultWriter",
        DummyWriter,
    )

    operator = ProfileMeshTableOperator(
        task_id="profile_users",
        config_path=str(config_path),
        table="users",
        schema="public",
    )

    class MockTI:
        def __init__(self):
            self.task_id = "profile_users"
            self.xcom_data = {}

        def xcom_push(self, key, value):
            self.xcom_data[key] = value

        def xcom_pull(self, task_ids, key, default=None):
            return self.xcom_data.get(key, default)

    mock_ti = MockTI()
    context = {"ti": mock_ti, "execution_date": datetime.utcnow()}

    result = operator.execute(context)

    assert result["dataset_name"] == "users"
    assert result["columns_profiled"] == 1
    assert "profiling_result" in mock_ti.xcom_data


def test_plan_sensor_detects_changes(tmp_path, monkeypatch):
    """Test that ProfileMeshPlanSensor detects plan changes."""
    airflow = pytest.importorskip("airflow")
    from profilemesh.integrations.airflow import ProfileMeshPlanSensor

    config_path = _write_config(tmp_path / "config.yml", ["users"])

    # Mock Variable.get/set
    cursor_storage = {}

    def mock_get(key, default_var=None):
        return cursor_storage.get(key, default_var)

    def mock_set(key, value):
        cursor_storage[key] = value

    monkeypatch.setattr("airflow.models.Variable.get", mock_get)
    monkeypatch.setattr("airflow.models.Variable.set", mock_set)

    sensor = ProfileMeshPlanSensor(
        task_id="plan_sensor",
        config_path=str(config_path),
        poke_interval=60,
    )

    class MockTI:
        def __init__(self):
            self.task_id = "plan_sensor"
            self.xcom_data = {}

        def xcom_push(self, key, value):
            self.xcom_data[key] = value

        def xcom_pull(self, task_ids, key, default=None):
            return self.xcom_data.get(key, default)

    mock_ti = MockTI()
    context = {"ti": mock_ti, "execution_date": datetime.utcnow()}

    # First poke - should detect change (no previous cursor)
    result = sensor.poke(context)
    assert result is True
    assert "plan_change_metadata" in mock_ti.xcom_data
    metadata = mock_ti.xcom_data["plan_change_metadata"]
    assert "users" in metadata["changed_tables"]
    assert cursor_storage  # Cursor should be stored

    # Second poke - no change
    mock_ti.xcom_data.clear()
    result = sensor.poke(context)
    assert result is False

    # Modify config - should detect change
    _write_config(config_path, ["users", "events"])
    result = sensor.poke(context)
    assert result is True
    assert "plan_change_metadata" in mock_ti.xcom_data
    metadata = mock_ti.xcom_data["plan_change_metadata"]
    assert "events" in metadata["changed_tables"]


def test_plan_sensor_cursor_behavior(tmp_path, monkeypatch):
    """Test cursor persistence in ProfileMeshPlanSensor."""
    airflow = pytest.importorskip("airflow")
    from profilemesh.integrations.airflow import ProfileMeshPlanSensor

    config_path = _write_config(tmp_path / "config.yml", ["users"])

    cursor_storage = {}

    def mock_get(key, default_var=None):
        return cursor_storage.get(key, default_var)

    def mock_set(key, value):
        cursor_storage[key] = value

    monkeypatch.setattr("airflow.models.Variable.get", mock_get)
    monkeypatch.setattr("airflow.models.Variable.set", mock_set)

    sensor = ProfileMeshPlanSensor(
        task_id="plan_sensor",
        config_path=str(config_path),
    )

    class MockTI:
        def __init__(self):
            self.xcom_data = {}

        def xcom_push(self, key, value):
            self.xcom_data[key] = value

        def xcom_pull(self, task_ids, key, default=None):
            return self.xcom_data.get(key, default)

    context = {"ti": MockTI(), "execution_date": datetime.utcnow()}

    # First poke
    result = sensor.poke(context)
    assert result is True
    first_cursor = cursor_storage.get("profilemesh_plan_cursor")
    assert first_cursor is not None

    # Parse cursor to verify structure
    cursor_data = json.loads(first_cursor)
    assert "signature" in cursor_data
    assert "tables" in cursor_data
    assert "users" in cursor_data["tables"]


def test_create_profiling_task_group(tmp_path):
    """Test that create_profiling_task_group generates tasks."""
    airflow = pytest.importorskip("airflow")
    from airflow import DAG
    from profilemesh.integrations.airflow import create_profiling_task_group

    config_path = _write_config(tmp_path / "config.yml", ["users", "events"])

    with DAG("test_dag", start_date=datetime(2024, 1, 1)) as dag:
        task_group = create_profiling_task_group(
            group_id="profiling_tasks",
            config_path=str(config_path),
        )

        # Check that task group was created
        assert task_group is not None
        assert len(task_group.children) == 2  # Two tables

        # Check task IDs
        task_ids = {task.task_id for task in task_group.children.values()}
        assert "users" in task_ids
        assert "events" in task_ids


def test_operator_handles_no_results(tmp_path, monkeypatch):
    """Test operator behavior when profiling returns no results."""
    airflow = pytest.importorskip("airflow")
    from profilemesh.integrations.airflow import ProfileMeshProfilingOperator

    config_path = _write_config(tmp_path / "config.yml", ["users"])

    def fake_profile_empty(self, table_patterns):
        return []

    monkeypatch.setattr(
        "profilemesh.integrations.airflow.operators.ProfileEngine.profile",
        fake_profile_empty,
    )

    operator = ProfileMeshProfilingOperator(
        task_id="test_profiling",
        config_path=str(config_path),
    )

    class MockTI:
        def xcom_push(self, key, value):
            pass

        def xcom_pull(self, task_ids, key, default=None):
            return default

    context = {"ti": MockTI(), "execution_date": datetime.utcnow()}

    with pytest.raises(ValueError, match="No profiling results returned"):
        operator.execute(context)


def test_operator_with_specific_tables(tmp_path, monkeypatch):
    """Test operator with specific table patterns."""
    airflow = pytest.importorskip("airflow")
    from profilemesh.integrations.airflow import ProfileMeshProfilingOperator

    config_path = _write_config(tmp_path / "config.yml", ["users", "events", "logs"])

    profiled_tables = []

    def fake_profile_tracking(self, table_patterns):
        for pattern in table_patterns:
            profiled_tables.append(pattern.table)
        return [_fake_result(pattern.table) for pattern in table_patterns]

    class DummyWriter:
        def __init__(self, *_args, **_kwargs):
            pass

        def write_results(self, *_args, **_kwargs):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        "profilemesh.integrations.airflow.operators.ProfileEngine.profile",
        fake_profile_tracking,
    )
    monkeypatch.setattr(
        "profilemesh.integrations.airflow.operators.ResultWriter",
        DummyWriter,
    )

    # Only profile specific tables
    operator = ProfileMeshProfilingOperator(
        task_id="test_profiling",
        config_path=str(config_path),
        table_patterns=[
            {"schema": "public", "table": "users"},
            {"schema": "public", "table": "events"},
        ],
    )

    class MockTI:
        def __init__(self):
            self.xcom_data = {}

        def xcom_push(self, key, value):
            self.xcom_data[key] = value

        def xcom_pull(self, task_ids, key, default=None):
            return self.xcom_data.get(key, default)

    context = {"ti": MockTI(), "execution_date": datetime.utcnow()}

    result = operator.execute(context)

    assert len(profiled_tables) == 2
    assert "users" in profiled_tables
    assert "events" in profiled_tables
    assert "logs" not in profiled_tables
    assert result["tables_profiled"] == 2

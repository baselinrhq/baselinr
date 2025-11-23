import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml

# Skip entire test module if Dagster is not available or has import issues
try:
    from baselinr.integrations.dagster import (
        BaselinrResource,
        build_baselinr_definitions,
        create_profiling_assets,
    )
    from baselinr.integrations.dagster.sensors import baselinr_plan_sensor
    from baselinr.profiling.core import ProfilingResult

    DAGSTER_TESTS_AVAILABLE = True
except (ImportError, Exception) as e:
    # Dagster not installed or has compatibility issues (e.g., Pydantic v2)
    DAGSTER_TESTS_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason=f"Dagster integration not available: {e}")


def _write_config(path: Path, tables) -> Path:
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


def _fake_result(table_pattern):
    result = ProfilingResult(
        run_id="fake-run",
        dataset_name=table_pattern.table,
        schema_name=table_pattern.schema_,
        profiled_at=datetime.utcnow(),
    )
    result.columns = [{"column_name": "id", "metrics": {"count": 10}}]
    result.metadata = {"row_count": 10}
    return result


def test_asset_factory_emits_metadata(tmp_path, monkeypatch):
    if not DAGSTER_TESTS_AVAILABLE:
        pytest.skip("Dagster integration not available")
    try:
        from dagster import AssetKey, materialize
    except ImportError:
        pytest.skip("Dagster not installed")

    config_path = _write_config(tmp_path / "config.yml", ["users"])

    def fake_profile(self, table_patterns):
        return [_fake_result(table_patterns[0])]

    class DummyWriter:
        def __init__(self, *_args, **_kwargs):
            self.closed = False

        def write_results(self, *_args, **_kwargs):
            return None

        def close(self):
            self.closed = True

    monkeypatch.setattr("baselinr.integrations.dagster.assets.ProfileEngine.profile", fake_profile)
    monkeypatch.setattr("baselinr.integrations.dagster.assets.ResultWriter", DummyWriter)

    assets = create_profiling_assets(str(config_path), asset_name_prefix="mesh")
    user_asset = next(asset_def for asset_def in assets if AssetKey("mesh_users") in asset_def.keys)

    result = materialize(
        assets=[user_asset],
        resources={"baselinr": BaselinrResource(config_path=str(config_path))},
    )

    assert result.success
    mats = result.asset_materializations_for_node("mesh_users")
    assert mats, "expected asset materializations"
    metadata = mats[-1].metadata
    assert "drift_strategy" in metadata
    assert metadata["drift_strategy"].text == "absolute_threshold"
    assert metadata["requested_metrics"].data == ["count", "null_count"]


def test_plan_sensor_cursor_behavior(tmp_path):
    if not DAGSTER_TESTS_AVAILABLE:
        pytest.skip("Dagster integration not available")
    try:
        from dagster import build_sensor_context
    except ImportError:
        pytest.skip("Dagster not installed")

    config_path = _write_config(tmp_path / "config.yml", ["users"])
    sensor_def = baselinr_plan_sensor(
        config_path=str(config_path),
        job_name="baselinr_profile_all",
        asset_prefix="mesh",
        minimum_interval_seconds=1,
    )

    first_context = build_sensor_context()
    first_requests = list(sensor_def(first_context))
    assert len(first_requests) == 1
    first_cursor = first_context.cursor
    assert first_cursor

    # No change -> no run request
    second_context = build_sensor_context(cursor=first_cursor)
    assert list(sensor_def(second_context)) == []

    # Add a new table -> triggers run
    _write_config(config_path, ["users", "events"])
    third_context = build_sensor_context(cursor=first_cursor)
    third_requests = list(sensor_def(third_context))
    assert len(third_requests) == 1
    request = third_requests[0]
    tables = json.loads(request.tags["baselinr/changed_tables"])
    assert any(name.endswith("events") for name in tables)
    assert request.run_config["baselinr"]["metrics_requested"] >= 2


def test_build_definitions_wires_assets(tmp_path):
    if not DAGSTER_TESTS_AVAILABLE:
        pytest.skip("Dagster integration not available")
    try:
        from dagster import Definitions
    except ImportError:
        pytest.skip("Dagster not installed")

    config_path = _write_config(tmp_path / "config.yml", ["users"])
    defs = build_baselinr_definitions(
        config_path=str(config_path),
        asset_prefix="mesh",
        job_name="mesh_job",
    )

    job_def = defs.get_job_def("mesh_job")
    assert job_def is not None

    asset_graph = defs.resolve_asset_graph()
    asset_keys = {key.to_user_string() for key in asset_graph.get_all_asset_keys()}
    assert "mesh_users" in asset_keys
    assert "mesh_summary" in asset_keys

    sensor_def = defs.get_sensor_def("mesh_plan_sensor")
    assert sensor_def is not None

    assert "baselinr" in defs.resources


def test_asset_factory_with_pattern_based_selection(tmp_path, monkeypatch):
    """Test that create_profiling_assets works with pattern-based selection (select_schema)."""
    if not DAGSTER_TESTS_AVAILABLE:
        pytest.skip("Dagster integration not available")
    try:
        from dagster import AssetKey
    except ImportError:
        pytest.skip("Dagster not installed")

    # Create config with select_schema pattern (the bug scenario)
    config = {
        "environment": "test",
        "source": {
            "type": "sqlite",
            "database": "source.db",
            "filepath": str(tmp_path / "source.db"),
        },
        "storage": {
            "connection": {
                "type": "sqlite",
                "database": "results.db",
                "filepath": str(tmp_path / "results.db"),
            },
            "results_table": "baselinr_results",
            "runs_table": "baselinr_runs",
        },
        "profiling": {
            "tables": [
                {"schema": "public", "select_schema": True}
            ],
            "metrics": ["count", "null_count"],
            "compute_histograms": False,
        },
    }
    config_path = tmp_path / "config_patterns.yml"
    config_path.write_text(yaml.safe_dump(config))

    # Mock connector to return tables when list_tables is called
    def mock_list_tables(self, schema=None):
        # Return mock tables for the public schema
        if schema == "public" or schema is None:
            return ["users", "orders", "products"]
        return []

    def mock_list_schemas(self):
        return ["public"]

    # Mock the connector methods
    monkeypatch.setattr(
        "baselinr.connectors.sqlite.SQLiteConnector.list_tables", mock_list_tables
    )
    monkeypatch.setattr(
        "baselinr.connectors.sqlite.SQLiteConnector.list_schemas", mock_list_schemas
    )
    monkeypatch.setattr(
        "baselinr.connectors.base.BaseConnector.list_tables", mock_list_tables
    )
    monkeypatch.setattr(
        "baselinr.connectors.base.BaseConnector.list_schemas", mock_list_schemas
    )

    # This should not raise "Table name must be set" error
    # The bug would have caused an AssertionError here
    assets = create_profiling_assets(str(config_path), asset_name_prefix="test")

    # Should have created assets for each expanded table (users, orders, products) plus summary
    assert len(assets) == 4  # 3 table assets + 1 summary asset

    # Verify asset keys exist for the expanded tables
    all_keys = set()
    for asset_def in assets:
        all_keys.update(key.to_user_string() for key in asset_def.keys)

    assert "test_users" in all_keys
    assert "test_orders" in all_keys
    assert "test_products" in all_keys
    assert "test_summary" in all_keys
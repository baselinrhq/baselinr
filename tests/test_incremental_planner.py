"""Tests for incremental planner and change detection decisions."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from baselinr.config.schema import (
    BaselinrConfig,
    ConnectionConfig,
    IncrementalConfig,
    ProfilingConfig,
    StorageConfig,
    TablePattern,
)
from baselinr.incremental.change_detection import ChangeSummary
from baselinr.incremental.planner import IncrementalPlanner
from baselinr.incremental.state import TableState


@pytest.fixture
def incremental_config(tmp_path):
    """Base configuration with incremental profiling enabled."""
    storage_path = tmp_path / "state.db"
    return BaselinrConfig(
        environment="test",
        source=ConnectionConfig(type="postgres", host="localhost", port=5432, database="warehouse"),
        storage=StorageConfig(
            connection=ConnectionConfig(
                type="sqlite",
                database=str(storage_path),
                filepath=str(storage_path),
            ),
            results_table="baselinr_results",
            runs_table="baselinr_runs",
        ),
        profiling=ProfilingConfig(tables=[TablePattern(table="events", schema_="public")]),
        incremental=IncrementalConfig(enabled=True),
    )


def _mock_planner(incremental_config, state: TableState, summary: ChangeSummary):
    state_store = MagicMock()
    state_store.load_state.return_value = state
    state_store.record_decision = MagicMock()

    change_detector = MagicMock()
    change_detector.summarize.return_value = summary

    connector = MagicMock()
    connector.config.database = "warehouse"

    with (
        patch("baselinr.incremental.planner.create_connector", return_value=connector),
        patch("baselinr.incremental.planner.build_change_detector", return_value=change_detector),
    ):
        planner = IncrementalPlanner(incremental_config, state_store=state_store)
    return planner, state_store


def test_incremental_planner_skips_when_snapshot_matches(incremental_config):
    """Planner should skip tables when snapshot IDs match."""
    state = TableState(
        table_name="events",
        schema_name="public",
        snapshot_id="snap-1",
        last_profiled_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    summary = ChangeSummary(snapshot_id="snap-1", row_count=100)

    planner, state_store = _mock_planner(incremental_config, state, summary)
    plan = planner.get_tables_to_run(datetime.now(timezone.utc))

    assert plan.decisions[0].action == "skip"
    state_store.record_decision.assert_called_once()


def test_incremental_planner_partial_when_partitions_detected(incremental_config):
    """Planner should request partial runs when change detector surfaces partitions."""
    incremental_config.incremental.partial_profiling.enabled = True
    state = TableState(
        table_name="events",
        schema_name="public",
        snapshot_id="snap-1",
        last_profiled_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    summary = ChangeSummary(
        snapshot_id="snap-2",
        row_count=500,
        changed_partitions=["2025-01-01", "2025-01-02"],
    )

    planner, _ = _mock_planner(incremental_config, state, summary)
    plan = planner.get_tables_to_run(datetime.now(timezone.utc))

    decision = plan.decisions[0]
    assert decision.action == "partial"
    assert decision.changed_partitions == ["2025-01-01", "2025-01-02"]


def test_incremental_planner_cost_sampling(incremental_config):
    """Cost guardrails configured for sampling should downgrade to sampling action."""
    incremental_config.incremental.cost_controls.enabled = True
    incremental_config.incremental.cost_controls.max_rows_scanned = 10
    incremental_config.incremental.cost_controls.fallback_strategy = "sample"

    state = TableState(
        table_name="events",
        schema_name="public",
        snapshot_id=None,
        last_profiled_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    summary = ChangeSummary(
        snapshot_id="snap-3",
        row_count=10_000,
    )

    planner, _ = _mock_planner(incremental_config, state, summary)
    plan = planner.get_tables_to_run(datetime.now(timezone.utc))

    decision = plan.decisions[0]
    assert decision.action == "sample"
    assert decision.use_sampling is True

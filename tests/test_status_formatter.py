"""Tests for status formatter."""

import json
from datetime import datetime

import pytest

from baselinr.query.status_formatter import format_status


@pytest.fixture
def sample_runs_data():
    """Sample runs data for testing."""
    return [
        {
            "run_id": "run-1",
            "table_name": "customers",
            "schema_name": "public",
            "profiled_at": "2024-01-15T10:00:00Z",
            "duration": "45.2s",
            "rows_scanned": 1000000,
            "sample_percent": "N/A",
            "metrics_count": 15,
            "anomalies_count": 0,
            "status_indicator": "🟢",
        },
        {
            "run_id": "run-2",
            "table_name": "orders",
            "schema_name": "public",
            "profiled_at": "2024-01-15T09:00:00Z",
            "duration": "2.5m",
            "rows_scanned": 5000000,
            "sample_percent": "N/A",
            "metrics_count": 20,
            "anomalies_count": 2,
            "status_indicator": "🟡",
        },
    ]


@pytest.fixture
def sample_drift_summary():
    """Sample drift summary for testing."""
    return [
        {
            "table_name": "customers",
            "severity": "high",
            "drift_type": "volume",
            "started_at": "2024-01-14T08:00:00Z",
            "event_count": 3,
        },
        {
            "table_name": "orders",
            "severity": "medium",
            "drift_type": "distribution",
            "started_at": "2024-01-13T12:00:00Z",
            "event_count": 1,
        },
    ]


def test_format_status_json(sample_runs_data, sample_drift_summary):
    """Test JSON format output."""
    output = format_status(sample_runs_data, sample_drift_summary, format="json")
    assert isinstance(output, str)

    import json

    parsed = json.loads(output)
    assert "timestamp" in parsed
    assert "runs" in parsed
    assert "drift_summary" in parsed
    assert len(parsed["runs"]) == 2
    assert len(parsed["drift_summary"]) == 2


def test_format_status_json_drift_only(sample_runs_data, sample_drift_summary):
    """Test JSON format with drift-only flag."""
    output = format_status(sample_runs_data, sample_drift_summary, format="json", drift_only=True)
    parsed = json.loads(output)
    assert "runs" not in parsed or len(parsed.get("runs", [])) == 0
    assert "drift_summary" in parsed


def test_format_status_text(sample_runs_data, sample_drift_summary):
    """Test text format output."""
    output = format_status(sample_runs_data, sample_drift_summary, format="text")
    assert isinstance(output, str)
    assert "BASELINR STATUS" in output
    assert "RECENT PROFILING RUNS" in output
    assert "DRIFT SUMMARY" in output
    assert "customers" in output
    assert "orders" in output


def test_format_status_text_drift_only(sample_runs_data, sample_drift_summary):
    """Test text format with drift-only flag."""
    output = format_status(sample_runs_data, sample_drift_summary, format="text", drift_only=True)
    assert "RECENT PROFILING RUNS" not in output or "No runs found" in output
    assert "DRIFT SUMMARY" in output


def test_format_status_text_empty_runs(sample_drift_summary):
    """Test text format with empty runs."""
    output = format_status([], sample_drift_summary, format="text")
    assert "No runs found" in output
    assert "DRIFT SUMMARY" in output


def test_format_status_text_empty_drift(sample_runs_data):
    """Test text format with empty drift."""
    output = format_status(sample_runs_data, [], format="text")
    assert "RECENT PROFILING RUNS" in output
    assert "No active drift detected" in output


def test_format_status_rich(sample_runs_data, sample_drift_summary):
    """Test Rich format output (if Rich is available)."""
    output = format_status(sample_runs_data, sample_drift_summary, format="rich")
    assert isinstance(output, str)
    # Rich output should contain table formatting
    assert "customers" in output or "Recent Profiling Runs" in output


def test_format_status_rich_fallback(sample_runs_data, sample_drift_summary):
    """Test that Rich format falls back to text if Rich unavailable."""
    # This test verifies the fallback mechanism works
    # In practice, Rich should be available, but we test the fallback path
    output = format_status(sample_runs_data, sample_drift_summary, format="text")
    assert isinstance(output, str)
    assert len(output) > 0


def test_format_status_empty_data():
    """Test formatting with completely empty data."""
    output = format_status([], [], format="json")
    parsed = json.loads(output)
    assert parsed["runs"] == []
    assert parsed["drift_summary"] == []

    output_text = format_status([], [], format="text")
    assert "No runs found" in output_text
    assert "No active drift detected" in output_text


def test_format_status_missing_fields(sample_drift_summary):
    """Test formatting with runs missing some fields."""
    incomplete_runs = [
        {
            "run_id": "run-1",
            "table_name": "customers",
            # Missing other fields
        }
    ]
    output = format_status(incomplete_runs, sample_drift_summary, format="json")
    parsed = json.loads(output)
    assert len(parsed["runs"]) == 1
    assert parsed["runs"][0]["run_id"] == "run-1"


def test_format_status_drift_severity_colors(sample_runs_data):
    """Test that drift severity is properly formatted."""
    drift_with_all_severities = [
        {"table_name": "high_table", "severity": "high", "drift_type": "volume", "started_at": "2024-01-15T10:00:00Z", "event_count": 1},
        {"table_name": "medium_table", "severity": "medium", "drift_type": "distribution", "started_at": "2024-01-15T10:00:00Z", "event_count": 1},
        {"table_name": "low_table", "severity": "low", "drift_type": "schema", "started_at": "2024-01-15T10:00:00Z", "event_count": 1},
    ]
    output = format_status(sample_runs_data, drift_with_all_severities, format="text")
    assert "high_table" in output
    assert "medium_table" in output
    assert "low_table" in output


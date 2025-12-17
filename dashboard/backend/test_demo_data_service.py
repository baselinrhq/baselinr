"""
Unit tests for DemoDataService.

Tests data loading, filtering, sorting, pagination, and all API methods.
"""

import pytest
import os
from datetime import datetime, timedelta
from demo_data_service import DemoDataService


@pytest.fixture
def service():
    """Create DemoDataService instance for testing."""
    return DemoDataService()


@pytest.mark.asyncio
async def test_data_loading(service):
    """Test that all JSON files are loaded correctly."""
    assert len(service.runs_raw) > 0, "Runs should be loaded"
    assert len(service.metrics_raw) > 0, "Metrics should be loaded"
    assert len(service.drift_events_raw) > 0, "Drift events should be loaded"
    assert len(service.tables_raw) > 0, "Tables should be loaded"
    assert len(service.validation_results_raw) > 0, "Validations should be loaded"
    assert 'nodes' in service.lineage_raw, "Lineage should have nodes"
    assert 'edges' in service.lineage_raw, "Lineage should have edges"
    assert 'generated_at' in service.metadata, "Metadata should be loaded"


@pytest.mark.asyncio
async def test_data_indices(service):
    """Test that lookup indices are built correctly."""
    assert len(service.runs_by_id) == len(service.runs_raw), "All runs should be indexed"
    
    # Check metrics index
    total_metrics_indexed = sum(len(metrics) for metrics in service.metrics_by_run_id.values())
    assert total_metrics_indexed == len(service.metrics_raw), "All metrics should be indexed"
    
    # Check drift index
    total_drift_indexed = sum(len(events) for events in service.drift_by_run_id.values())
    assert total_drift_indexed == len(service.drift_events_raw), "All drift events should be indexed"


@pytest.mark.asyncio
async def test_get_runs_no_filters(service):
    """Test get_runs without any filters."""
    runs = await service.get_runs(limit=10)
    
    assert len(runs) <= 10, "Should respect limit"
    assert all(hasattr(r, 'run_id') for r in runs), "All runs should have run_id"
    assert all(hasattr(r, 'warehouse_type') for r in runs), "All runs should have warehouse_type"


@pytest.mark.asyncio
async def test_get_runs_filter_by_warehouse(service):
    """Test filtering runs by warehouse."""
    warehouses = await service.get_warehouses()
    assert len(warehouses) > 0, "Should have warehouses"
    
    test_warehouse = warehouses[0]
    runs = await service.get_runs(warehouse=test_warehouse)
    
    assert all(r.warehouse_type == test_warehouse for r in runs), \
        f"All runs should be from {test_warehouse}"


@pytest.mark.asyncio
async def test_get_runs_filter_by_table(service):
    """Test filtering runs by table name."""
    # Get a table name from the data
    if service.runs_raw:
        test_table = service.runs_raw[0]['dataset_name']
        runs = await service.get_runs(table=test_table)
        
        assert all(r.dataset_name == test_table for r in runs), \
            f"All runs should be for table {test_table}"
        assert len(runs) > 0, "Should find runs for the table"


@pytest.mark.asyncio
async def test_get_runs_filter_by_status(service):
    """Test filtering runs by status."""
    runs = await service.get_runs(status="completed")
    
    assert all(r.status == "completed" for r in runs), "All runs should have completed status"


@pytest.mark.asyncio
async def test_get_runs_filter_by_date_range(service):
    """Test filtering runs by date range."""
    now = datetime.now()
    start_date = now - timedelta(days=30)
    
    runs = await service.get_runs(start_date=start_date)
    
    assert all(r.profiled_at >= start_date for r in runs), \
        "All runs should be within date range"


@pytest.mark.asyncio
async def test_get_runs_sorting_desc(service):
    """Test sorting runs by date descending."""
    runs = await service.get_runs(sort_by="profiled_at", sort_order="desc", limit=10)
    
    if len(runs) > 1:
        for i in range(len(runs) - 1):
            assert runs[i].profiled_at >= runs[i + 1].profiled_at, \
                "Runs should be sorted by date descending"


@pytest.mark.asyncio
async def test_get_runs_sorting_asc(service):
    """Test sorting runs by date ascending."""
    runs = await service.get_runs(sort_by="profiled_at", sort_order="asc", limit=10)
    
    if len(runs) > 1:
        for i in range(len(runs) - 1):
            assert runs[i].profiled_at <= runs[i + 1].profiled_at, \
                "Runs should be sorted by date ascending"


@pytest.mark.asyncio
async def test_get_runs_pagination(service):
    """Test pagination of runs."""
    # Get first page
    page1 = await service.get_runs(limit=5, offset=0)
    # Get second page
    page2 = await service.get_runs(limit=5, offset=5)
    
    assert len(page1) <= 5, "First page should have at most 5 items"
    assert len(page2) <= 5, "Second page should have at most 5 items"
    
    # Pages should not overlap
    page1_ids = {r.run_id for r in page1}
    page2_ids = {r.run_id for r in page2}
    assert page1_ids.isdisjoint(page2_ids), "Pages should not overlap"


@pytest.mark.asyncio
async def test_get_run_details(service):
    """Test getting detailed run information."""
    # Get a run ID
    runs = await service.get_runs(limit=1)
    assert len(runs) > 0, "Should have at least one run"
    
    run_id = runs[0].run_id
    details = await service.get_run_details(run_id)
    
    assert details is not None, "Should find run details"
    assert details.run_id == run_id, "Run ID should match"
    assert len(details.columns) > 0, "Should have column metrics"
    assert all(hasattr(c, 'column_name') for c in details.columns), \
        "All columns should have names"


@pytest.mark.asyncio
async def test_get_run_details_invalid_id(service):
    """Test getting run details with invalid ID."""
    details = await service.get_run_details("invalid_run_id_12345")
    assert details is None, "Should return None for invalid run ID"


@pytest.mark.asyncio
async def test_get_drift_alerts_no_filters(service):
    """Test getting drift alerts without filters."""
    alerts = await service.get_drift_alerts(limit=10)
    
    assert len(alerts) <= 10, "Should respect limit"
    assert all(hasattr(a, 'event_id') for a in alerts), "All alerts should have event_id"
    assert all(hasattr(a, 'severity') for a in alerts), "All alerts should have severity"


@pytest.mark.asyncio
async def test_get_drift_alerts_filter_by_severity(service):
    """Test filtering drift alerts by severity."""
    alerts = await service.get_drift_alerts(severity="high")
    
    assert all(a.severity == "high" for a in alerts), "All alerts should be high severity"


@pytest.mark.asyncio
async def test_get_drift_alerts_filter_by_table(service):
    """Test filtering drift alerts by table."""
    if service.drift_events_raw:
        test_table = service.drift_events_raw[0]['table_name']
        alerts = await service.get_drift_alerts(table=test_table)
        
        assert all(a.table_name == test_table for a in alerts), \
            f"All alerts should be for table {test_table}"


@pytest.mark.asyncio
async def test_get_dashboard_metrics(service):
    """Test getting dashboard metrics."""
    metrics = await service.get_dashboard_metrics()
    
    assert metrics.total_runs > 0, "Should have run count"
    assert metrics.total_tables > 0, "Should have table count"
    assert len(metrics.kpis) > 0, "Should have KPIs"
    assert len(metrics.run_trend) > 0, "Should have run trend"
    assert len(metrics.recent_runs) > 0, "Should have recent runs"
    assert metrics.validation_pass_rate is not None, "Should have validation pass rate"


@pytest.mark.asyncio
async def test_get_warehouses(service):
    """Test getting list of warehouses."""
    warehouses = await service.get_warehouses()
    
    assert len(warehouses) > 0, "Should have warehouses"
    assert all(isinstance(w, str) for w in warehouses), "All warehouses should be strings"
    # Should be sorted
    assert warehouses == sorted(warehouses), "Warehouses should be sorted"


@pytest.mark.asyncio
async def test_get_tables_no_filters(service):
    """Test getting tables without filters."""
    response = await service.get_tables(limit=10)
    
    assert response.total > 0, "Should have tables"
    assert len(response.tables) <= 10, "Should respect limit"
    assert all(hasattr(t, 'table_name') for t in response.tables), \
        "All tables should have names"


@pytest.mark.asyncio
async def test_get_tables_filter_by_warehouse(service):
    """Test filtering tables by warehouse."""
    warehouses = await service.get_warehouses()
    test_warehouse = warehouses[0]
    
    response = await service.get_tables(warehouse=test_warehouse)
    
    assert all(t.warehouse_type == test_warehouse for t in response.tables), \
        f"All tables should be from {test_warehouse}"


@pytest.mark.asyncio
async def test_get_tables_search(service):
    """Test searching tables by name."""
    # Get a table name
    if service.tables_raw:
        test_table = service.tables_raw[0]['table_name']
        search_term = test_table[:3]  # Use first 3 chars
        
        response = await service.get_tables(search=search_term)
        
        assert any(search_term.lower() in t.table_name.lower() 
                  for t in response.tables), "Should find matching tables"


@pytest.mark.asyncio
async def test_get_tables_pagination(service):
    """Test table pagination."""
    page1 = await service.get_tables(limit=5, offset=0)
    page2 = await service.get_tables(limit=5, offset=5)
    
    assert len(page1.tables) <= 5, "First page should have at most 5 items"
    assert page1.page == 1, "First page number should be 1"
    assert page2.page == 2, "Second page number should be 2"


@pytest.mark.asyncio
async def test_get_table_metrics(service):
    """Test getting table metrics."""
    if service.tables_raw:
        test_table = service.tables_raw[0]['table_name']
        test_schema = service.tables_raw[0].get('schema_name')
        
        metrics = await service.get_table_metrics(test_table, test_schema)
        
        assert metrics is not None, "Should find table metrics"
        assert metrics.table_name == test_table, "Table name should match"
        assert len(metrics.columns) > 0, "Should have column metrics"
        assert len(metrics.row_count_trend) > 0, "Should have row count trend"


@pytest.mark.asyncio
async def test_get_table_overview(service):
    """Test getting table overview."""
    if service.tables_raw:
        test_table = service.tables_raw[0]['table_name']
        test_schema = service.tables_raw[0].get('schema_name')
        
        overview = await service.get_table_overview(test_table, test_schema)
        
        assert overview is not None, "Should find table overview"
        assert overview.table_name == test_table, "Table name should match"
        assert len(overview.recent_runs) > 0, "Should have recent runs"


@pytest.mark.asyncio
async def test_get_table_validation_results(service):
    """Test getting validation results for a table."""
    if service.validation_results_raw:
        test_table = service.validation_results_raw[0]['table_name']
        
        results = await service.get_table_validation_results(test_table)
        
        assert results is not None, "Should get validation results"
        assert results.table_name == test_table, "Table name should match"
        assert 'total' in results.summary, "Summary should have total"


@pytest.mark.asyncio
async def test_get_validation_summary(service):
    """Test getting validation summary."""
    summary = await service.get_validation_summary()
    
    assert summary.total_validations > 0, "Should have validations"
    assert summary.pass_rate >= 0 and summary.pass_rate <= 100, \
        "Pass rate should be between 0 and 100"
    assert len(summary.by_rule_type) > 0, "Should have breakdown by rule type"


@pytest.mark.asyncio
async def test_get_validation_results_no_filters(service):
    """Test getting validation results without filters."""
    response = await service.get_validation_results(limit=10)
    
    assert response.total > 0, "Should have validation results"
    assert len(response.results) <= 10, "Should respect limit"


@pytest.mark.asyncio
async def test_get_validation_results_filter_passed(service):
    """Test filtering validation results by passed status."""
    response = await service.get_validation_results(passed=True, limit=10)
    
    assert all(r.passed for r in response.results), \
        "All results should have passed=True"


@pytest.mark.asyncio
async def test_get_validation_results_filter_rule_type(service):
    """Test filtering validation results by rule type."""
    if service.validation_results_raw:
        test_rule_type = service.validation_results_raw[0]['rule_type']
        response = await service.get_validation_results(rule_type=test_rule_type)
        
        assert all(r.rule_type == test_rule_type for r in response.results), \
            f"All results should be {test_rule_type} rule type"


@pytest.mark.asyncio
async def test_get_validation_result_details(service):
    """Test getting validation result details."""
    if service.validation_results_raw:
        result_id = service.validation_results_raw[0]['id']
        details = await service.get_validation_result_details(result_id)
        
        assert details is not None, "Should find result details"
        assert details.result.id == result_id, "Result ID should match"
        assert details.run_info is not None, "Should have run info"


@pytest.mark.asyncio
async def test_get_validation_failure_samples(service):
    """Test getting validation failure samples."""
    # Find a failed validation
    failed = [v for v in service.validation_results_raw if not v.get('passed')]
    if failed:
        result_id = failed[0]['id']
        samples = await service.get_validation_failure_samples(result_id, limit=5)
        
        assert samples is not None, "Should get failure samples"
        assert samples.result_id == result_id, "Result ID should match"
        assert len(samples.sample_failures) > 0, "Should have sample failures"


@pytest.mark.asyncio
async def test_get_drift_summary(service):
    """Test getting drift summary."""
    summary = await service.get_drift_summary()
    
    assert summary.total_events > 0, "Should have drift events"
    assert len(summary.by_severity) > 0, "Should have severity breakdown"
    assert len(summary.top_affected_tables) > 0, "Should have affected tables"
    assert len(summary.trending) > 0, "Should have trend data"


@pytest.mark.asyncio
async def test_get_drift_details(service):
    """Test getting drift details."""
    if service.drift_events_raw:
        event_id = service.drift_events_raw[0]['event_id']
        details = await service.get_drift_details(event_id)
        
        assert details is not None, "Should find drift details"
        assert details.event.event_id == event_id, "Event ID should match"
        assert details.baseline_metrics is not None, "Should have baseline metrics"
        assert details.current_metrics is not None, "Should have current metrics"


@pytest.mark.asyncio
async def test_get_drift_impact(service):
    """Test getting drift impact."""
    if service.drift_events_raw:
        event_id = service.drift_events_raw[0]['event_id']
        impact = await service.get_drift_impact(event_id)
        
        assert impact is not None, "Should get drift impact"
        assert impact.event_id == event_id, "Event ID should match"
        assert impact.impact_score >= 0 and impact.impact_score <= 1, \
            "Impact score should be between 0 and 1"
        assert len(impact.recommendations) > 0, "Should have recommendations"


@pytest.mark.asyncio
async def test_get_lineage_impact(service):
    """Test getting lineage impact."""
    if service.tables_raw:
        test_table = service.tables_raw[0]['table_name']
        test_schema = service.tables_raw[0].get('schema_name')
        
        impact = await service.get_lineage_impact(test_table, test_schema)
        
        assert impact is not None, "Should get lineage impact"
        assert impact.table == test_table, "Table name should match"
        assert impact.impact_score >= 0 and impact.impact_score <= 1, \
            "Impact score should be between 0 and 1"


@pytest.mark.asyncio
async def test_date_parsing(service):
    """Test datetime parsing from ISO strings."""
    # Test with ISO string
    iso_str = "2025-12-16T00:00:00+00:00"
    parsed = service._parse_datetime(iso_str)
    assert isinstance(parsed, datetime), "Should parse to datetime"
    
    # Test with datetime object (should return as-is)
    dt = datetime.now()
    parsed = service._parse_datetime(dt)
    assert parsed == dt, "Should return datetime as-is"


@pytest.mark.asyncio
async def test_combined_filters(service):
    """Test combining multiple filters."""
    warehouses = await service.get_warehouses()
    if warehouses:
        test_warehouse = warehouses[0]
        runs = await service.get_runs(
            warehouse=test_warehouse,
            status="completed",
            limit=5
        )
        
        assert all(r.warehouse_type == test_warehouse for r in runs), \
            "All runs should match warehouse filter"
        assert all(r.status == "completed" for r in runs), \
            "All runs should match status filter"
        assert len(runs) <= 5, "Should respect limit"


def test_service_initialization():
    """Test that service initializes correctly."""
    service = DemoDataService()
    assert service is not None, "Service should initialize"
    assert len(service.runs_raw) > 0, "Should load data on init"


def test_service_with_custom_data_dir():
    """Test service initialization with custom data directory."""
    # Use default data dir
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "demo_data")
    
    service = DemoDataService(data_dir=data_dir)
    assert service is not None, "Service should initialize with custom dir"
    assert len(service.runs_raw) > 0, "Should load data from custom dir"


if __name__ == "__main__":
    # Run a quick test
    import asyncio
    
    print("Running quick smoke test...")
    service = DemoDataService()
    
    async def smoke_test():
        runs = await service.get_runs(limit=5)
        print(f"[OK] Loaded {len(runs)} runs")
        
        metrics = await service.get_dashboard_metrics()
        print(f"[OK] Dashboard metrics: {metrics.total_runs} runs, {metrics.total_tables} tables")
        
        warehouses = await service.get_warehouses()
        print(f"[OK] Found {len(warehouses)} warehouses: {', '.join(warehouses)}")
        
        drift_summary = await service.get_drift_summary()
        print(f"[OK] Drift summary: {drift_summary.total_events} events")
        
        validation_summary = await service.get_validation_summary()
        print(f"[OK] Validation summary: {validation_summary.pass_rate:.1f}% pass rate")
        
        print("\n[SUCCESS] All smoke tests passed!")
    
    asyncio.run(smoke_test())


"""
Performance benchmarks for DemoDataService.

Tests that all queries complete within target time (<100ms for most operations).
"""

import asyncio
import time
from demo_data_service import DemoDataService


async def benchmark_operation(name, operation, target_ms=100):
    """Benchmark a single operation."""
    start = time.time()
    result = await operation()
    elapsed_ms = (time.time() - start) * 1000
    
    status = "[OK]" if elapsed_ms < target_ms else "[SLOW]"
    print(f"{status} {name}: {elapsed_ms:.2f}ms (target: <{target_ms}ms)")
    
    return elapsed_ms, result


async def run_benchmarks():
    """Run all performance benchmarks."""
    print("=" * 60)
    print("DemoDataService Performance Benchmarks")
    print("=" * 60)
    print()
    
    # Initialize service (measure load time)
    print("Initializing service...")
    start = time.time()
    service = DemoDataService()
    init_time = (time.time() - start) * 1000
    print(f"[OK] Service initialization: {init_time:.2f}ms (target: <500ms)")
    print()
    
    results = {}
    
    # Core operations
    print("Core Operations:")
    results['get_runs'] = await benchmark_operation(
        "get_runs (limit=100)",
        lambda: service.get_runs(limit=100)
    )
    
    # Get a run ID for detail test
    runs = results['get_runs'][1]
    if runs:
        run_id = runs[0].run_id
        results['get_run_details'] = await benchmark_operation(
            "get_run_details",
            lambda: service.get_run_details(run_id)
        )
    
    results['get_dashboard_metrics'] = await benchmark_operation(
        "get_dashboard_metrics",
        lambda: service.get_dashboard_metrics()
    )
    print()
    
    # Filtering operations
    print("Filtering Operations:")
    warehouses = await service.get_warehouses()
    if warehouses:
        test_warehouse = warehouses[0]
        results['get_runs_filtered'] = await benchmark_operation(
            f"get_runs (warehouse={test_warehouse})",
            lambda: service.get_runs(warehouse=test_warehouse)
        )
    
    results['get_runs_date_range'] = await benchmark_operation(
        "get_runs (date range)",
        lambda: service.get_runs(start_date=None, end_date=None, limit=50)
    )
    print()
    
    # Table operations
    print("Table Operations:")
    results['get_tables'] = await benchmark_operation(
        "get_tables (limit=50)",
        lambda: service.get_tables(limit=50)
    )
    
    results['get_warehouses'] = await benchmark_operation(
        "get_warehouses",
        lambda: service.get_warehouses(),
        target_ms=10
    )
    
    # Get a table for detail tests
    tables_response = await service.get_tables(limit=1)
    if tables_response.tables:
        test_table = tables_response.tables[0].table_name
        test_schema = tables_response.tables[0].schema_name
        
        results['get_table_metrics'] = await benchmark_operation(
            f"get_table_metrics ({test_table})",
            lambda: service.get_table_metrics(test_table, test_schema)
        )
        
        results['get_table_overview'] = await benchmark_operation(
            f"get_table_overview ({test_table})",
            lambda: service.get_table_overview(test_table, test_schema)
        )
    print()
    
    # Drift operations
    print("Drift Operations:")
    results['get_drift_alerts'] = await benchmark_operation(
        "get_drift_alerts (limit=100)",
        lambda: service.get_drift_alerts(limit=100)
    )
    
    results['get_drift_summary'] = await benchmark_operation(
        "get_drift_summary",
        lambda: service.get_drift_summary()
    )
    
    # Get a drift event for detail test
    drift_alerts = await service.get_drift_alerts(limit=1)
    if drift_alerts:
        event_id = drift_alerts[0].event_id
        results['get_drift_details'] = await benchmark_operation(
            "get_drift_details",
            lambda: service.get_drift_details(event_id)
        )
        
        results['get_drift_impact'] = await benchmark_operation(
            "get_drift_impact",
            lambda: service.get_drift_impact(event_id)
        )
    print()
    
    # Validation operations
    print("Validation Operations:")
    results['get_validation_summary'] = await benchmark_operation(
        "get_validation_summary",
        lambda: service.get_validation_summary()
    )
    
    results['get_validation_results'] = await benchmark_operation(
        "get_validation_results (limit=100)",
        lambda: service.get_validation_results(limit=100)
    )
    
    # Get a validation result for detail test
    validation_results = await service.get_validation_results(limit=1)
    if validation_results.results:
        result_id = validation_results.results[0].id
        results['get_validation_result_details'] = await benchmark_operation(
            "get_validation_result_details",
            lambda: service.get_validation_result_details(result_id)
        )
    print()
    
    # Lineage operations
    print("Lineage Operations:")
    if tables_response.tables:
        test_table = tables_response.tables[0].table_name
        test_schema = tables_response.tables[0].schema_name
        results['get_lineage_impact'] = await benchmark_operation(
            "get_lineage_impact",
            lambda: service.get_lineage_impact(test_table, test_schema)
        )
    print()
    
    # Summary statistics
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    times = [elapsed for elapsed, _ in results.values()]
    avg_time = sum(times) / len(times)
    max_time = max(times)
    
    print(f"Total operations tested: {len(results)}")
    print(f"Average time: {avg_time:.2f}ms")
    print(f"Max time: {max_time:.2f}ms")
    
    # Check if all operations met target
    slow_ops = [name for name, (elapsed, _) in results.items() if elapsed > 100]
    if slow_ops:
        print(f"\nSlow operations (>100ms): {len(slow_ops)}")
        for op in slow_ops:
            print(f"  - {op}: {results[op][0]:.2f}ms")
    else:
        print(f"\n[SUCCESS] All operations completed within target time!")
    
    # Check initialization time
    if init_time > 500:
        print(f"\n[WARNING] Initialization time ({init_time:.2f}ms) exceeds target (500ms)")
    else:
        print(f"[OK] Initialization time within target")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_benchmarks())


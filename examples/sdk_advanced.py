"""
Baselinr SDK Advanced Example

This script demonstrates advanced usage of the Baselinr Python SDK:
1. Custom event hooks
2. Progress callbacks during profiling
3. Programmatic drift analysis
4. Querying anomalies
5. Status monitoring
"""

import sys
from pathlib import Path
from typing import Any

# Add parent directory to path to import baselinr
sys.path.insert(0, str(Path(__file__).parent.parent))

from baselinr import BaselinrClient


def progress_callback(current: int, total: int, table_name: str):
    """Progress callback for profiling."""
    print(f"  Profiling {table_name} ({current}/{total})...")


class CustomEventHook:
    """Custom event hook example."""

    def __init__(self, name: str):
        self.name = name
        self.events_received = []

    def handle_event(self, event: Any) -> None:
        """Handle an event."""
        self.events_received.append(event)
        print(f"[{self.name}] Event: {event.event_type}")


def main():
    """Run advanced SDK examples."""

    print("=" * 60)
    print("Baselinr SDK Advanced Example")
    print("=" * 60)

    # 1. Initialize client
    print("\n[1/6] Initializing Baselinr client...")
    config_path = Path(__file__).parent / "config.yml"

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        print("Please ensure you have a config.yml file in the examples directory.")
        return 1

    client = BaselinrClient(config_path=str(config_path))
    print(f"✓ Client initialized (environment: {client.config.environment})")

    # 2. Build plan with verbose output
    print("\n[2/6] Building detailed profiling plan...")
    try:
        plan = client.plan()
        print(f"✓ Plan details:")
        print(f"  - Total tables: {plan.total_tables}")
        print(f"  - Estimated metrics: {plan.estimated_metrics}")
        print(f"  - Drift strategy: {plan.drift_strategy}")
        print(f"  - Source: {plan.source_type} ({plan.source_database})")

        # Show table details
        if plan.tables:
            print(f"\n  Table plans:")
            for table_plan in plan.tables[:3]:
                print(f"    - {table_plan.full_name}: {table_plan.status}")
                if table_plan.partition_config:
                    print(f"      Partition: {table_plan.partition_config}")
                if table_plan.sampling_config:
                    print(f"      Sampling: {table_plan.sampling_config}")
    except Exception as e:
        print(f"✗ Failed to build plan: {e}")
        return 1

    # 3. Profile with progress callback
    print("\n[3/6] Profiling tables with progress callback...")
    try:
        results = client.profile(progress_callback=progress_callback)

        if not results:
            print("Warning: No profiling results generated")
            return 1

        print(f"✓ Profiled {len(results)} tables")
        for result in results:
            print(f"  - {result.dataset_name}:")
            print(f"    Columns: {len(result.columns)}")
            print(f"    Row count: {result.metadata.get('row_count', 'N/A')}")
            print(f"    Run ID: {result.run_id[:8]}...")
    except Exception as e:
        print(f"✗ Profiling failed: {e}")
        return 1

    # 4. Advanced drift analysis
    print("\n[4/6] Performing advanced drift analysis...")
    try:
        if results:
            first_table = results[0].dataset_name

            # Detect drift with custom baseline
            drift_report = client.detect_drift(dataset_name=first_table)

            print(f"✓ Drift analysis for {first_table}:")
            print(f"  Baseline run: {drift_report.baseline_run_id[:8]}...")
            print(f"  Current run: {drift_report.current_run_id[:8]}...")

            # Analyze column drifts
            column_drifts = drift_report.column_drifts
            print(f"  Total column drifts: {len(column_drifts)}")

            if column_drifts:
                print(f"  Drift details:")
                for drift in column_drifts[:3]:
                    if drift.drift_detected:
                        print(f"    - {drift.column_name}.{drift.metric_name}:")
                        print(f"      Severity: {drift.drift_severity}")
                        print(f"      Change: {drift.change_percent:.2f}%")
                        if drift.metadata:
                            print(f"      Metadata: {drift.metadata}")

            # Schema changes
            if drift_report.schema_changes:
                print(f"  Schema changes: {len(drift_report.schema_changes)}")
                for change in drift_report.schema_changes:
                    print(f"    - {change}")

    except ValueError as e:
        print(f"ℹ Drift detection skipped: {e}")
    except Exception as e:
        print(f"✗ Drift analysis failed: {e}")

    # 5. Query anomalies
    print("\n[5/6] Querying anomaly events...")
    try:
        anomalies = client.query_anomalies(days=7, severity="high", limit=10)

        if anomalies:
            print(f"✓ Found {len(anomalies)} high-severity anomalies:")
            for anomaly in anomalies[:3]:
                print(f"  - {anomaly.get('table_name')}.{anomaly.get('column_name')}:")
                print(f"    Metric: {anomaly.get('metric_name')}")
                print(f"    Value: {anomaly.get('current_value')}")
                print(f"    Timestamp: {anomaly.get('timestamp')}")
        else:
            print("✓ No high-severity anomalies found in the last 7 days")
    except Exception as e:
        print(f"✗ Failed to query anomalies: {e}")

    # 6. Comprehensive status check
    print("\n[6/6] Getting comprehensive status...")
    try:
        status = client.get_status(days=7, limit=20)

        runs_data = status.get("runs_data", [])
        drift_summary = status.get("drift_summary", [])

        print(f"✓ Status summary:")
        print(f"  Recent runs: {len(runs_data)}")
        print(f"  Active drift events: {len(drift_summary)}")

        # Analyze run health
        healthy_runs = sum(
            1 for r in runs_data if not r.get("has_drift") and r.get("anomalies_count", 0) == 0
        )
        print(f"  Healthy runs: {healthy_runs}/{len(runs_data)}")

        # Show drift summary
        if drift_summary:
            print(f"\n  Drift events by table:")
            for drift in drift_summary[:3]:
                print(f"    - {drift.get('table_name')}: {drift.get('drift_count', 0)} drifts")

        # Show recent runs with issues
        runs_with_issues = [
            r for r in runs_data if r.get("has_drift") or r.get("anomalies_count", 0) > 0
        ]
        if runs_with_issues:
            print(f"\n  Runs with issues: {len(runs_with_issues)}")
            for run in runs_with_issues[:3]:
                issues = []
                if run.get("has_drift"):
                    issues.append(f"drift ({run.get('drift_severity')})")
                if run.get("anomalies_count", 0) > 0:
                    issues.append(f"{run.get('anomalies_count')} anomalies")
                print(f"    - {run.get('table_name')}: {', '.join(issues)}")

    except Exception as e:
        print(f"✗ Failed to get status: {e}")

    # 7. Query specific run details
    print("\n[7/7] Querying detailed run information...")
    try:
        if results:
            run_id = results[0].run_id
            run_details = client.query_run_details(run_id, dataset_name=results[0].dataset_name)

            if run_details:
                print(f"✓ Run details for {run_id[:8]}...")
                run_info = run_details.get("run", {})
                print(f"  Table: {run_info.get('dataset_name')}")
                print(f"  Profiled at: {run_info.get('profiled_at')}")
                print(f"  Row count: {run_info.get('row_count')}")
                print(f"  Column count: {run_info.get('column_count')}")

                metrics = run_details.get("metrics", {})
                print(f"  Metrics captured: {len(metrics)} column-metric combinations")

    except Exception as e:
        print(f"✗ Failed to query run details: {e}")

    print("\n" + "=" * 60)
    print("SDK Advanced example completed!")
    print("=" * 60)
    print("\nKey takeaways:")
    print("1. SDK provides clean, programmatic access to all Baselinr features")
    print("2. Progress callbacks allow custom monitoring during profiling")
    print("3. Query methods enable flexible data exploration")
    print("4. Status methods provide comprehensive health monitoring")

    return 0


if __name__ == "__main__":
    sys.exit(main())

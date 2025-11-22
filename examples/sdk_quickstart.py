"""
Baselinr SDK Quick Start Example

This script demonstrates basic usage of the Baselinr Python SDK:
1. Initialize client
2. Build execution plan
3. Profile tables
4. Detect drift
5. Query results
"""

import sys
from pathlib import Path

# Add parent directory to path to import baselinr
sys.path.insert(0, str(Path(__file__).parent.parent))

from baselinr import BaselinrClient


def main():
    """Run a quick SDK example."""

    print("=" * 60)
    print("Baselinr SDK Quick Start Example")
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

    # 2. Build execution plan
    print("\n[2/6] Building profiling execution plan...")
    try:
        plan = client.plan()
        print(f"✓ Plan built: {plan.total_tables} tables, ~{plan.estimated_metrics} metrics")
        print(f"  Tables to profile: {', '.join([t.full_name for t in plan.tables[:3]])}")
        if len(plan.tables) > 3:
            print(f"  ... and {len(plan.tables) - 3} more")
    except Exception as e:
        print(f"✗ Failed to build plan: {e}")
        return 1

    # 3. Profile tables
    print("\n[3/6] Profiling tables...")
    try:
        results = client.profile()
        if not results:
            print("Warning: No profiling results generated")
            return 1

        print(f"✓ Profiled {len(results)} tables:")
        for result in results:
            row_count = result.metadata.get("row_count", "N/A")
            print(f"  - {result.dataset_name}: {len(result.columns)} columns, " f"{row_count} rows")
    except Exception as e:
        print(f"✗ Profiling failed: {e}")
        return 1

    # 4. Detect drift (if we have previous runs)
    print("\n[4/6] Checking for drift...")
    try:
        if results:
            first_table = results[0].dataset_name
            drift_report = client.detect_drift(dataset_name=first_table)

            print(f"✓ Drift detection completed for {first_table}")
            print(f"  - Total drifts detected: {drift_report.summary.get('total_drifts', 0)}")
            print(f"  - Schema changes: {len(drift_report.schema_changes)}")
            drift_by_severity = drift_report.summary.get("drift_by_severity", {})
            print(f"  - High severity drifts: {drift_by_severity.get('high', 0)}")

    except ValueError as e:
        print(f"ℹ Drift detection skipped: {e}")
        print("  (This is normal for the first run)")
    except Exception as e:
        print(f"✗ Drift detection failed: {e}")

    # 5. Query recent runs
    print("\n[5/6] Querying recent profiling runs...")
    try:
        runs = client.query_runs(days=7, limit=10)
        print(f"✓ Found {len(runs)} runs in the last 7 days:")
        for run in runs[:3]:
            print(f"  - {run.dataset_name}: {run.profiled_at}")
        if len(runs) > 3:
            print(f"  ... and {len(runs) - 3} more")
    except Exception as e:
        print(f"✗ Failed to query runs: {e}")

    # 6. Get status summary
    print("\n[6/6] Getting status summary...")
    try:
        status = client.get_status(days=7, limit=10)
        drift_summary = status.get("drift_summary", [])
        runs_data = status.get("runs_data", [])
        print(f"✓ Status summary:")
        print(f"  - Recent runs: {len(runs_data)}")
        print(f"  - Active drift events: {len(drift_summary)}")
    except Exception as e:
        print(f"✗ Failed to get status: {e}")

    print("\n" + "=" * 60)
    print("SDK Quick start completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Explore the SDK API documentation")
    print("2. Check out examples/sdk_advanced.py for more advanced usage")
    print("3. Build custom profiling pipelines using the SDK")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Baselinr Quick Start Example

This script demonstrates basic usage of Baselinr:
1. Load configuration
2. Profile tables
3. Write results to storage
4. Detect drift
"""

import sys
from pathlib import Path

# Add parent directory to path to import baselinr
sys.path.insert(0, str(Path(__file__).parent.parent))

from baselinr.config.loader import ConfigLoader
from baselinr.drift.detector import DriftDetector
from baselinr.events import EventBus, LoggingAlertHook
from baselinr.profiling.core import ProfileEngine
from baselinr.storage.writer import ResultWriter


def main():
    """Run a quick profiling example."""

    print("=" * 60)
    print("Baselinr Quick Start Example")
    print("=" * 60)

    # 1. Load configuration
    print("\n[1/4] Loading configuration...")
    config_path = Path(__file__).parent / "config.yml"

    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        print("Please ensure you have a config.yml file in the examples directory.")
        return 1

    config = ConfigLoader.load_from_file(str(config_path))
    print(f"✓ Configuration loaded (environment: {config.environment})")

    # Initialize event bus with hooks (if configured)
    event_bus = None
    if config.hooks.enabled and config.hooks.hooks:
        event_bus = EventBus()
        for hook_config in config.hooks.hooks:
            if hook_config.enabled and hook_config.type == "logging":
                event_bus.register(LoggingAlertHook(log_level=hook_config.log_level))
        if event_bus.hook_count > 0:
            print(f"✓ Event bus initialized with {event_bus.hook_count} hook(s)")

    # 2. Profile tables
    print("\n[2/4] Profiling tables...")
    engine = ProfileEngine(config, event_bus=event_bus)
    results = engine.profile()

    if not results:
        print("Warning: No profiling results generated")
        return 1

    print(f"✓ Profiled {len(results)} tables:")
    for result in results:
        print(
            f"  - {result.dataset_name}: {len(result.columns)} columns, "
            f"{result.metadata.get('row_count', 'N/A')} rows"
        )

    # 3. Write results to storage
    print("\n[3/4] Writing results to storage...")
    writer = ResultWriter(config.storage)
    writer.write_results(
        results,
        environment=config.environment,
        enable_enrichment=config.profiling.enable_enrichment,
    )
    print(f"✓ Results written to storage")
    writer.close()

    # 4. Try drift detection (if we have previous runs)
    print("\n[4/4] Checking for drift...")
    try:
        detector = DriftDetector(config.storage, config.drift_detection, event_bus=event_bus)

        # Try to detect drift for the first table
        first_table = results[0].dataset_name
        report = detector.detect_drift(dataset_name=first_table)

        print(f"✓ Drift detection completed for {first_table}")
        print(f"  - Total drifts detected: {report.summary['total_drifts']}")
        print(f"  - Schema changes: {report.summary['schema_changes']}")
        print(f"  - High severity drifts: {report.summary['drift_by_severity']['high']}")

    except ValueError as e:
        print(f"ℹ Drift detection skipped: {e}")
        print("  (This is normal for the first run)")

    print("\n" + "=" * 60)
    print("Quick start completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Check the profiling results in your database")
    print("2. Run the script again to see drift detection in action")
    print("3. Explore the Dagster integration for orchestration")

    return 0


if __name__ == "__main__":
    sys.exit(main())

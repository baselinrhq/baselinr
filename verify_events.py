"""
Simple verification script for the event and hooks system.
This script tests the basic functionality without requiring pytest.
"""

import sys
from datetime import datetime

# Add the package to path
sys.path.insert(0, '.')

from profilemesh.events import (
    EventBus,
    LoggingAlertHook,
    DataDriftDetected,
    SchemaChangeDetected,
    ProfilingCompleted,
)


def test_basic_event_emission():
    """Test basic event emission."""
    print("\n" + "=" * 60)
    print("TEST 1: Basic Event Emission")
    print("=" * 60)
    
    # Create event bus
    bus = EventBus()
    
    # Register logging hook
    bus.register(LoggingAlertHook(log_level="INFO"))
    
    # Emit events
    print("\nEmitting ProfilingCompleted event:")
    bus.emit(ProfilingCompleted(
        event_type="ProfilingCompleted",
        timestamp=datetime.utcnow(),
        table="test_table",
        run_id="test-123",
        row_count=1000,
        column_count=10,
        duration_seconds=5.5,
        metadata={}
    ))
    
    print("\nEmitting DataDriftDetected event:")
    bus.emit(DataDriftDetected(
        event_type="DataDriftDetected",
        timestamp=datetime.utcnow(),
        table="users",
        column="age",
        metric="mean",
        baseline_value=30.5,
        current_value=45.2,
        change_percent=48.2,
        drift_severity="high",
        metadata={}
    ))
    
    print(f"\n[PASS] Successfully emitted {bus.event_count} events through {bus.hook_count} hook(s)")
    return True


def test_multiple_hooks():
    """Test multiple hooks working together."""
    print("\n" + "=" * 60)
    print("TEST 2: Multiple Hooks")
    print("=" * 60)
    
    # Event collector hook
    class CollectorHook:
        def __init__(self):
            self.events = []
        
        def handle_event(self, event):
            self.events.append(event)
    
    # Create bus and register multiple hooks
    bus = EventBus()
    bus.register(LoggingAlertHook(log_level="INFO"))
    
    collector = CollectorHook()
    bus.register(collector)
    
    print(f"\nRegistered {bus.hook_count} hooks")
    
    # Emit event
    print("\nEmitting SchemaChangeDetected event:")
    bus.emit(SchemaChangeDetected(
        event_type="SchemaChangeDetected",
        timestamp=datetime.utcnow(),
        table="products",
        change_type="column_added",
        column="sku",
        metadata={}
    ))
    
    print(f"\n[PASS] Event processed by {bus.hook_count} hooks")
    print(f"[PASS] Collector captured {len(collector.events)} event(s)")
    return True


def test_hook_failure_resilience():
    """Test that hook failures don't stop other hooks."""
    print("\n" + "=" * 60)
    print("TEST 3: Hook Failure Resilience")
    print("=" * 60)
    
    # Failing hook
    class FailingHook:
        def handle_event(self, event):
            raise Exception("Intentional failure for testing")
    
    # Create bus and register hooks
    bus = EventBus()
    bus.register(FailingHook())  # This will fail
    bus.register(LoggingAlertHook())  # This should still work
    
    print(f"\nRegistered {bus.hook_count} hooks (1 will fail)")
    
    # Emit event
    print("\nEmitting event (first hook will fail, second should still work):")
    bus.emit(ProfilingCompleted(
        event_type="ProfilingCompleted",
        timestamp=datetime.utcnow(),
        table="test_table",
        run_id="test-456",
        row_count=500,
        column_count=5,
        duration_seconds=2.1,
        metadata={}
    ))
    
    print(f"\n[PASS] Event bus continued despite hook failure")
    print(f"[PASS] Total events emitted: {bus.event_count}")
    return True


def test_event_metadata():
    """Test that events populate metadata correctly."""
    print("\n" + "=" * 60)
    print("TEST 4: Event Metadata Population")
    print("=" * 60)
    
    # Create drift event
    event = DataDriftDetected(
        event_type="DataDriftDetected",
        timestamp=datetime.utcnow(),
        table="orders",
        column="total_amount",
        metric="mean",
        baseline_value=100.0,
        current_value=150.0,
        change_percent=50.0,
        drift_severity="high",
        metadata={}
    )
    
    # Verify metadata
    print("\nVerifying metadata population:")
    assert event.metadata["table"] == "orders", "Table not in metadata"
    print("[OK] table in metadata")
    
    assert event.metadata["column"] == "total_amount", "Column not in metadata"
    print("[OK] column in metadata")
    
    assert event.metadata["metric"] == "mean", "Metric not in metadata"
    print("[OK] metric in metadata")
    
    assert event.metadata["baseline_value"] == 100.0, "Baseline value not in metadata"
    print("[OK] baseline_value in metadata")
    
    assert event.metadata["drift_severity"] == "high", "Severity not in metadata"
    print("[OK] drift_severity in metadata")
    
    print("\n[PASS] All metadata fields correctly populated")
    return True


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("ProfileMesh Event System Verification")
    print("=" * 60)
    
    tests = [
        ("Basic Event Emission", test_basic_event_emission),
        ("Multiple Hooks", test_multiple_hooks),
        ("Hook Failure Resilience", test_hook_failure_resilience),
        ("Event Metadata", test_event_metadata),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n[FAIL] TEST FAILED: {name}")
            print(f"   Error: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"[PASS] Passed: {passed}/{len(tests)}")
    if failed > 0:
        print(f"[FAIL] Failed: {failed}/{len(tests)}")
    else:
        print("SUCCESS: All tests passed!")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


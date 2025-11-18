"""
Example demonstrating the event and hooks system in Baselinr.

This example shows how to:
1. Create an event bus
2. Register multiple hooks (built-in and custom)
3. Emit events during profiling
4. Create custom hooks for specific use cases
"""

from datetime import datetime

from baselinr.events import (
    BaseEvent,
    DataDriftDetected,
    EventBus,
    LoggingAlertHook,
    ProfilingCompleted,
    SchemaChangeDetected,
)


# Example 1: Basic Event Bus Usage
def example_basic_event_bus():
    """Demonstrate basic event bus with logging hook."""
    print("=" * 60)
    print("Example 1: Basic Event Bus with Logging")
    print("=" * 60)

    # Create event bus
    bus = EventBus()

    # Register logging hook
    bus.register(LoggingAlertHook(log_level="INFO"))

    # Emit some events
    bus.emit(
        ProfilingCompleted(
            event_type="ProfilingCompleted",
            timestamp=datetime.utcnow(),
            table="customers",
            run_id="demo-run-1",
            row_count=1000,
            column_count=10,
            duration_seconds=2.5,
            metadata={},
        )
    )

    bus.emit(
        DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="orders",
            column="total_amount",
            metric="mean",
            baseline_value=100.50,
            current_value=150.75,
            change_percent=50.0,
            drift_severity="high",
            metadata={},
        )
    )

    print(f"\nEmitted {bus.event_count} events through {bus.hook_count} hook(s)\n")


# Example 2: Custom Hook - Collect Events
class EventCollectorHook:
    """Custom hook that collects events for later analysis."""

    def __init__(self):
        self.events = []

    def handle_event(self, event: BaseEvent) -> None:
        """Collect event."""
        self.events.append(event)

    def get_drift_events(self):
        """Get only drift detection events."""
        return [e for e in self.events if isinstance(e, DataDriftDetected)]

    def get_high_severity_drifts(self):
        """Get high-severity drift events."""
        return [e for e in self.get_drift_events() if e.drift_severity == "high"]


def example_custom_collector_hook():
    """Demonstrate custom hook that collects events."""
    print("=" * 60)
    print("Example 2: Custom Event Collector Hook")
    print("=" * 60)

    # Create event bus
    bus = EventBus()

    # Register custom collector hook
    collector = EventCollectorHook()
    bus.register(collector)

    # Emit various events
    bus.emit(
        DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="orders",
            column="total_amount",
            metric="mean",
            baseline_value=100.0,
            current_value=150.0,
            change_percent=50.0,
            drift_severity="high",
            metadata={},
        )
    )

    bus.emit(
        DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="customers",
            column="age",
            metric="mean",
            baseline_value=30.0,
            current_value=32.0,
            change_percent=6.7,
            drift_severity="low",
            metadata={},
        )
    )

    bus.emit(
        SchemaChangeDetected(
            event_type="SchemaChangeDetected",
            timestamp=datetime.utcnow(),
            table="products",
            change_type="column_added",
            column="sku",
            metadata={},
        )
    )

    # Analyze collected events
    print(f"\nCollected {len(collector.events)} total events")
    print(f"Drift events: {len(collector.get_drift_events())}")
    print(f"High-severity drifts: {len(collector.get_high_severity_drifts())}")

    print("\nHigh-severity drift details:")
    for event in collector.get_high_severity_drifts():
        print(
            f"  - {event.table}.{event.column}: "
            f"{event.change_percent:+.1f}% change in {event.metric}"
        )
    print()


# Example 3: Custom Hook - Alert Filter
class FilteredAlertHook:
    """Custom hook that only alerts on specific conditions."""

    def __init__(self, min_severity="medium", alert_function=None):
        self.min_severity = min_severity
        self.alert_function = alert_function or self._default_alert
        self.severity_order = {"low": 1, "medium": 2, "high": 3}

    def handle_event(self, event: BaseEvent) -> None:
        """Handle event with filtering."""
        # Only process drift events
        if not isinstance(event, DataDriftDetected):
            return

        # Check severity threshold
        event_severity = self.severity_order.get(event.drift_severity, 0)
        min_severity = self.severity_order.get(self.min_severity, 0)

        if event_severity >= min_severity:
            self.alert_function(event)

    def _default_alert(self, event: DataDriftDetected):
        """Default alert implementation."""
        print(f"🚨 ALERT: {event.drift_severity.upper()} drift detected!")
        print(f"   Table: {event.table}")
        print(f"   Column: {event.column}")
        print(f"   Metric: {event.metric}")
        print(f"   Change: {event.change_percent:+.1f}%")


def example_filtered_alert_hook():
    """Demonstrate filtered alert hook."""
    print("=" * 60)
    print("Example 3: Filtered Alert Hook (medium+ severity)")
    print("=" * 60)

    # Create event bus
    bus = EventBus()

    # Register filtered alert hook
    alert_hook = FilteredAlertHook(min_severity="medium")
    bus.register(alert_hook)

    # Emit events with different severities
    print("\nEmitting low-severity drift (should be filtered):")
    bus.emit(
        DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="customers",
            column="age",
            metric="mean",
            baseline_value=30.0,
            current_value=32.0,
            change_percent=6.7,
            drift_severity="low",
            metadata={},
        )
    )

    print("\nEmitting medium-severity drift (should alert):")
    bus.emit(
        DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="orders",
            column="total_amount",
            metric="mean",
            baseline_value=100.0,
            current_value=120.0,
            change_percent=20.0,
            drift_severity="medium",
            metadata={},
        )
    )

    print("\nEmitting high-severity drift (should alert):")
    bus.emit(
        DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="products",
            column="price",
            metric="mean",
            baseline_value=50.0,
            current_value=80.0,
            change_percent=60.0,
            drift_severity="high",
            metadata={},
        )
    )
    print()


# Example 4: Multiple Hooks
def example_multiple_hooks():
    """Demonstrate using multiple hooks together."""
    print("=" * 60)
    print("Example 4: Multiple Hooks Working Together")
    print("=" * 60)

    # Create event bus
    bus = EventBus()

    # Register multiple hooks
    bus.register(LoggingAlertHook(log_level="INFO"))  # Log everything

    collector = EventCollectorHook()  # Collect for analysis
    bus.register(collector)

    alert_hook = FilteredAlertHook(min_severity="high")  # Alert on high severity
    bus.register(alert_hook)

    print(f"\nRegistered {bus.hook_count} hooks\n")

    # Emit a high-severity drift event
    print("Emitting high-severity drift event:")
    print("-" * 40)
    bus.emit(
        DataDriftDetected(
            event_type="DataDriftDetected",
            timestamp=datetime.utcnow(),
            table="transactions",
            column="amount",
            metric="mean",
            baseline_value=1000.0,
            current_value=2000.0,
            change_percent=100.0,
            drift_severity="high",
            metadata={},
        )
    )

    print("\n" + "=" * 40)
    print(f"Event processed by all {bus.hook_count} hooks")
    print(f"Collector has {len(collector.events)} event(s)")
    print()


# Example 5: Hook Error Handling
class FailingHook:
    """Hook that always fails (for demonstration)."""

    def handle_event(self, event: BaseEvent) -> None:
        """This hook always fails."""
        raise Exception("Simulated hook failure!")


def example_hook_error_handling():
    """Demonstrate that hook failures don't stop other hooks."""
    print("=" * 60)
    print("Example 5: Hook Error Handling")
    print("=" * 60)

    # Create event bus
    bus = EventBus()

    # Register a failing hook and a working hook
    bus.register(FailingHook())  # This will fail
    bus.register(LoggingAlertHook())  # This should still work

    print("\nEmitting event (first hook will fail, second should still work):")
    print("-" * 40)

    # Emit event
    bus.emit(
        ProfilingCompleted(
            event_type="ProfilingCompleted",
            timestamp=datetime.utcnow(),
            table="test_table",
            run_id="test-run",
            row_count=100,
            column_count=5,
            duration_seconds=1.0,
            metadata={},
        )
    )

    print("\n✅ Event bus continued despite hook failure\n")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Baselinr Event and Hooks System Examples")
    print("=" * 60 + "\n")

    example_basic_event_bus()
    example_custom_collector_hook()
    example_filtered_alert_hook()
    example_multiple_hooks()
    example_hook_error_handling()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60 + "\n")

    print("Next steps:")
    print("  1. Review docs/architecture/EVENTS_AND_HOOKS.md for detailed documentation")
    print("  2. Configure hooks in your config.yml")
    print("  3. Create custom hooks for your specific needs")
    print("  4. Integrate with your orchestration platform")
    print()


if __name__ == "__main__":
    main()

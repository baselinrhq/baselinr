"""
Alert hook protocol for Baselinr.

Defines the interface that all alert hooks must implement.
"""

from typing import Protocol

from .events import BaseEvent


class AlertHook(Protocol):
    """
    Protocol for alert hooks.

    All hooks must implement the handle_event method to process events.
    Hooks can perform any action such as logging, sending alerts, or
    persisting events to storage.
    """

    def handle_event(self, event: BaseEvent) -> None:
        """
        Handle an emitted event.

        Args:
            event: The event to handle

        Note:
            Implementations should handle exceptions internally to avoid
            disrupting other hooks or the event emission process.
        """
        ...

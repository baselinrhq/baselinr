"""
Event bus for managing and emitting events in Baselinr.

The EventBus is responsible for registering hooks and dispatching events
to all registered handlers.
"""

import logging
from typing import List

from .events import BaseEvent
from .hooks import AlertHook

logger = logging.getLogger(__name__)


class EventBus:
    """
    Central event bus for Baselinr.

    The event bus manages registered alert hooks and dispatches events
    to them. Hooks are called synchronously in the order they were registered.
    Hook failures are logged but do not prevent other hooks from executing.
    """

    def __init__(self):
        """Initialize the event bus with an empty hook list."""
        self.hooks: List[AlertHook] = []
        self._event_count = 0

    def register(self, hook: AlertHook) -> None:
        """
        Register an alert hook.

        Args:
            hook: An object implementing the AlertHook protocol
        """
        self.hooks.append(hook)
        logger.debug(f"Registered hook: {hook.__class__.__name__}")

    def unregister(self, hook: AlertHook) -> None:
        """
        Unregister an alert hook.

        Args:
            hook: The hook to remove
        """
        if hook in self.hooks:
            self.hooks.remove(hook)
            logger.debug(f"Unregistered hook: {hook.__class__.__name__}")

    def emit(self, event: BaseEvent) -> None:
        """
        Emit an event to all registered hooks.

        Args:
            event: The event to emit

        Note:
            Hooks are called synchronously. If a hook raises an exception,
            it is logged but does not prevent other hooks from executing.
        """
        self._event_count += 1
        logger.debug(f"Emitting event: {event.event_type} (total: {self._event_count})")

        for hook in self.hooks:
            try:
                hook.handle_event(event)
            except Exception as e:
                logger.warning(f"Event hook {hook.__class__.__name__} failed: {e}", exc_info=True)

    def clear_hooks(self) -> None:
        """Remove all registered hooks."""
        self.hooks.clear()
        logger.debug("Cleared all hooks")

    @property
    def event_count(self) -> int:
        """Get the total number of events emitted."""
        return int(self._event_count)

    @property
    def hook_count(self) -> int:
        """Get the number of registered hooks."""
        return len(self.hooks)  # type: ignore[no-any-return]

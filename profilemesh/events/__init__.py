"""
Event and alert hook system for ProfileMesh.

This module provides a lightweight, pluggable event emission system that allows
runtime events (like data drift or schema changes) to be emitted in-memory,
processed by multiple registered hooks, and optionally persisted or alerted.
"""

from .events import (
    BaseEvent,
    DataDriftDetected,
    SchemaChangeDetected,
    ProfilingStarted,
    ProfilingCompleted,
    ProfilingFailed,
    ProfilingSkipped,
)
from .hooks import AlertHook
from .event_bus import EventBus
from .builtin_hooks import LoggingAlertHook, SnowflakeEventHook, SQLEventHook

__all__ = [
    "BaseEvent",
    "DataDriftDetected",
    "SchemaChangeDetected",
    "ProfilingStarted",
    "ProfilingCompleted",
    "ProfilingFailed",
    "ProfilingSkipped",
    "AlertHook",
    "EventBus",
    "LoggingAlertHook",
    "SnowflakeEventHook",
    "SQLEventHook",
]


"""
Event and alert hook system for Baselinr.

This module provides a lightweight, pluggable event emission system that allows
runtime events (like data drift or schema changes) to be emitted in-memory,
processed by multiple registered hooks, and optionally persisted or alerted.
"""

from .builtin_hooks import LoggingAlertHook, SlackAlertHook, SnowflakeEventHook, SQLEventHook
from .event_bus import EventBus
from .events import (
    AnomalyDetected,
    BaseEvent,
    DataDriftDetected,
    ProfilingCompleted,
    ProfilingFailed,
    ProfilingSkipped,
    ProfilingStarted,
    QualityScoreDegraded,
    QualityScoreThresholdBreached,
    SchemaChangeDetected,
    ValidationFailed,
)
from .hooks import AlertHook

__all__ = [
    "BaseEvent",
    "AnomalyDetected",
    "DataDriftDetected",
    "SchemaChangeDetected",
    "ProfilingStarted",
    "ProfilingCompleted",
    "ProfilingFailed",
    "ProfilingSkipped",
    "QualityScoreDegraded",
    "QualityScoreThresholdBreached",
    "ValidationFailed",
    "AlertHook",
    "EventBus",
    "LoggingAlertHook",
    "SnowflakeEventHook",
    "SQLEventHook",
    "SlackAlertHook",
]

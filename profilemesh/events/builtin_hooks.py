"""
Built-in alert hook implementations for ProfileMesh.

Provides commonly used hooks for logging and persistence.
"""

import json
import logging
import uuid
from typing import Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine
from .events import BaseEvent

logger = logging.getLogger(__name__)


class LoggingAlertHook:
    """
    Simple logging hook that prints events to stdout.
    
    This hook is useful for development and debugging. Events are logged
    at INFO level with structured information.
    """
    
    def __init__(self, log_level: str = "INFO"):
        """
        Initialize the logging hook.
        
        Args:
            log_level: The logging level to use (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger = logging.getLogger(f"{__name__}.LoggingAlertHook")
    
    def handle_event(self, event: BaseEvent) -> None:
        """
        Log the event.
        
        Args:
            event: The event to log
        """
        self.logger.log(
            self.log_level,
            f"[ALERT] {event.event_type}: {event.metadata}"
        )


class SnowflakeEventHook:
    """
    Hook that persists events to a Snowflake table.
    
    This hook writes all events to a `profilemesh_events` table for
    historical tracking and analysis. The table must exist before using
    this hook.
    
    Table Schema:
        CREATE TABLE profilemesh_events (
            event_id VARCHAR PRIMARY KEY,
            event_type VARCHAR NOT NULL,
            table_name VARCHAR,
            column_name VARCHAR,
            metric_name VARCHAR,
            baseline_value FLOAT,
            current_value FLOAT,
            change_percent FLOAT,
            drift_severity VARCHAR,
            timestamp TIMESTAMP NOT NULL,
            metadata VARIANT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    
    def __init__(self, engine: Engine, table_name: str = "profilemesh_events"):
        """
        Initialize the Snowflake event hook.
        
        Args:
            engine: SQLAlchemy engine connected to Snowflake
            table_name: Name of the table to write events to
        """
        self.engine = engine
        self.table_name = table_name
    
    def handle_event(self, event: BaseEvent) -> None:
        """
        Persist the event to Snowflake.
        
        Args:
            event: The event to persist
        """
        try:
            event_id = str(uuid.uuid4())
            
            # Extract common fields from metadata
            metadata = event.metadata or {}
            table_name = metadata.get("table")
            column_name = metadata.get("column")
            metric_name = metadata.get("metric")
            baseline_value = metadata.get("baseline_value")
            current_value = metadata.get("current_value")
            change_percent = metadata.get("change_percent")
            drift_severity = metadata.get("drift_severity")
            
            # Convert metadata to JSON string for VARIANT column
            metadata_json = json.dumps(metadata)
            
            sql = text(f"""
                INSERT INTO {self.table_name}
                (event_id, event_type, table_name, column_name, metric_name,
                 baseline_value, current_value, change_percent, drift_severity,
                 timestamp, metadata)
                VALUES (
                    :event_id, :event_type, :table_name, :column_name, :metric_name,
                    :baseline_value, :current_value, :change_percent, :drift_severity,
                    :timestamp, PARSE_JSON(:metadata)
                )
            """)
            
            with self.engine.begin() as conn:
                conn.execute(
                    sql,
                    {
                        "event_id": event_id,
                        "event_type": event.event_type,
                        "table_name": table_name,
                        "column_name": column_name,
                        "metric_name": metric_name,
                        "baseline_value": baseline_value,
                        "current_value": current_value,
                        "change_percent": change_percent,
                        "drift_severity": drift_severity,
                        "timestamp": event.timestamp,
                        "metadata": metadata_json,
                    }
                )
            
            logger.debug(f"Persisted event {event_id} to {self.table_name}")
            
        except Exception as e:
            logger.error(f"Failed to persist event to Snowflake: {e}", exc_info=True)
            raise


class SQLEventHook:
    """
    Generic SQL hook that persists events to any SQL database.
    
    This hook is more flexible than SnowflakeEventHook and works with
    any database supported by SQLAlchemy (Postgres, MySQL, SQLite, etc.).
    
    Table Schema:
        CREATE TABLE profilemesh_events (
            event_id VARCHAR(36) PRIMARY KEY,
            event_type VARCHAR(100) NOT NULL,
            table_name VARCHAR(255),
            column_name VARCHAR(255),
            metric_name VARCHAR(100),
            baseline_value FLOAT,
            current_value FLOAT,
            change_percent FLOAT,
            drift_severity VARCHAR(20),
            timestamp TIMESTAMP NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    
    def __init__(self, engine: Engine, table_name: str = "profilemesh_events"):
        """
        Initialize the SQL event hook.
        
        Args:
            engine: SQLAlchemy engine
            table_name: Name of the table to write events to
        """
        self.engine = engine
        self.table_name = table_name
    
    def handle_event(self, event: BaseEvent) -> None:
        """
        Persist the event to the database.
        
        Args:
            event: The event to persist
        """
        try:
            event_id = str(uuid.uuid4())
            
            # Extract common fields from metadata
            metadata = event.metadata or {}
            table_name = metadata.get("table")
            column_name = metadata.get("column")
            metric_name = metadata.get("metric")
            baseline_value = metadata.get("baseline_value")
            current_value = metadata.get("current_value")
            change_percent = metadata.get("change_percent")
            drift_severity = metadata.get("drift_severity")
            
            # Convert metadata to JSON string
            metadata_json = json.dumps(metadata)
            
            sql = text(f"""
                INSERT INTO {self.table_name}
                (event_id, event_type, table_name, column_name, metric_name,
                 baseline_value, current_value, change_percent, drift_severity,
                 timestamp, metadata)
                VALUES (
                    :event_id, :event_type, :table_name, :column_name, :metric_name,
                    :baseline_value, :current_value, :change_percent, :drift_severity,
                    :timestamp, :metadata
                )
            """)
            
            with self.engine.begin() as conn:
                conn.execute(
                    sql,
                    {
                        "event_id": event_id,
                        "event_type": event.event_type,
                        "table_name": table_name,
                        "column_name": column_name,
                        "metric_name": metric_name,
                        "baseline_value": baseline_value,
                        "current_value": current_value,
                        "change_percent": change_percent,
                        "drift_severity": drift_severity,
                        "timestamp": event.timestamp,
                        "metadata": metadata_json,
                    }
                )
            
            logger.debug(f"Persisted event {event_id} to {self.table_name}")
            
        except Exception as e:
            logger.error(f"Failed to persist event to database: {e}", exc_info=True)
            raise


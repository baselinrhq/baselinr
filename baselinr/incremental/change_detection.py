"""
Change detection abstractions used by the incremental planner.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import text

from ..config.schema import IncrementalConfig, TablePattern
from ..connectors.base import BaseConnector

logger = logging.getLogger(__name__)


@dataclass
class ChangeSummary:
    """Lightweight snapshot describing table changes since the last run."""

    snapshot_id: Optional[str] = None
    change_token: Optional[str] = None
    row_count: Optional[int] = None
    bytes_scanned: Optional[int] = None
    changed_partitions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ChangeDetector:
    """Base interface for warehouse-specific change detectors."""

    def __init__(self, connector: BaseConnector, config: IncrementalConfig):
        self.connector = connector
        self.config = config

    def summarize(
        self, table: TablePattern, previous_snapshot_id: Optional[str] = None
    ) -> ChangeSummary:
        """
        Return a summary of changes for the table.

        Args:
            table: Table configuration.
            previous_snapshot_id: Snapshot ID from the last successful profile.
        """
        summary = self._collect_metadata(table, previous_snapshot_id)
        if summary.snapshot_id is None:
            summary.snapshot_id = self._build_snapshot_fingerprint(summary)
        return summary

    def _build_snapshot_fingerprint(self, summary: ChangeSummary) -> Optional[str]:
        """Fallback snapshot fingerprint derived from metadata values."""
        if not summary.metadata:
            return None
        parts = [f"{k}={summary.metadata[k]}" for k in sorted(summary.metadata)]
        return "|".join(parts)

    def _collect_metadata(
        self, table: TablePattern, previous_snapshot_id: Optional[str]
    ) -> ChangeSummary:
        raise NotImplementedError

    def _run_query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query using the connector's engine with optional params."""
        with self.connector.engine.connect() as conn:
            stmt = text(sql)
            result = conn.execute(stmt, params or {})
            return [dict(row) for row in result]


class NoopChangeDetector(ChangeDetector):
    """Fallback detector when a warehouse-specific implementation is unavailable."""

    def _collect_metadata(
        self, table: TablePattern, previous_snapshot_id: Optional[str]
    ) -> ChangeSummary:
        return ChangeSummary(metadata={"detector": "noop"})


class PostgresChangeDetector(ChangeDetector):
    """Uses pg_stat_all_tables counters to detect inserts/updates/deletes."""

    STATS_SQL = """
        SELECT
            n_live_tup,
            n_dead_tup,
            n_tup_ins,
            n_tup_upd,
            n_tup_del,
            last_autovacuum,
            last_autoanalyze,
            relpages
        FROM pg_stat_all_tables
        WHERE (%(schema)s IS NULL OR schemaname = %(schema)s)
          AND relname = %(table)s
    """

    def _collect_metadata(
        self, table: TablePattern, previous_snapshot_id: Optional[str]
    ) -> ChangeSummary:
        schema = table.schema_ or None
        rows = self._run_query(self.STATS_SQL, {"schema": schema, "table": table.table})
        if not rows:
            logger.warning("pg_stat_all_tables has no entry for %s.%s", schema, table.table)
            return ChangeSummary()

        stats = rows[0]
        snapshot_fingerprint = "|".join(
            str(stats.get(col))
            for col in ("n_tup_ins", "n_tup_upd", "n_tup_del", "last_autoanalyze")
        )

        metadata = {
            "n_live_tup": stats.get("n_live_tup"),
            "n_dead_tup": stats.get("n_dead_tup"),
            "n_tup_ins": stats.get("n_tup_ins"),
            "n_tup_upd": stats.get("n_tup_upd"),
            "n_tup_del": stats.get("n_tup_del"),
            "last_autovacuum": stats.get("last_autovacuum"),
            "last_autoanalyze": stats.get("last_autoanalyze"),
        }

        return ChangeSummary(
            snapshot_id=snapshot_fingerprint,
            change_token=str(stats.get("last_autoanalyze")),
            row_count=stats.get("n_live_tup"),
            bytes_scanned=(stats.get("relpages") or 0) * 8192,
            metadata=metadata,
        )


class SnowflakeChangeDetector(ChangeDetector):
    """Uses INFORMATION_SCHEMA.TABLES snapshot/row_count metadata."""

    TABLE_SQL = """
        SELECT
            last_altered,
            row_count,
            bytes
        FROM information_schema.tables
        WHERE table_catalog = %(database)s
          AND (%(schema)s IS NULL OR table_schema = %(schema)s)
          AND table_name = %(table)s
        LIMIT 1
    """

    def _collect_metadata(
        self, table: TablePattern, previous_snapshot_id: Optional[str]
    ) -> ChangeSummary:
        params = {
            "database": self.connector.config.database,
            "schema": table.schema_,
            "table": table.table.upper() if table.table else "",
        }
        rows = self._run_query(self.TABLE_SQL, params)
        if not rows:
            return ChangeSummary()

        record = rows[0]
        snapshot_id = str(record.get("last_altered"))
        return ChangeSummary(
            snapshot_id=snapshot_id,
            row_count=record.get("row_count"),
            bytes_scanned=record.get("bytes"),
            metadata={
                "last_altered": snapshot_id,
                "row_count": record.get("row_count"),
                "bytes": record.get("bytes"),
            },
        )


class BigQueryChangeDetector(ChangeDetector):
    """Uses INFORMATION_SCHEMA for table + partition metadata."""

    TABLE_SQL = """
        SELECT
            TIMESTAMP_MILLIS(last_modified_time) AS last_modified_time,
            row_count
        FROM `{}.{}.INFORMATION_SCHEMA.TABLES`
        WHERE table_name = @table_name
        LIMIT 1
    """

    PARTITION_SQL = """
        SELECT
            partition_id,
            TIMESTAMP_MILLIS(last_modified_time) AS last_modified_time,
            row_count
        FROM `{}.{}.INFORMATION_SCHEMA.PARTITIONS`
        WHERE table_name = @table_name
          AND TIMESTAMP_MILLIS(last_modified_time) >= @threshold
        ORDER BY last_modified_time DESC
        LIMIT @limit
    """

    def _collect_metadata(
        self, table: TablePattern, previous_snapshot_id: Optional[str]
    ) -> ChangeSummary:
        project = self.connector.config.database
        dataset = table.schema_ or self.connector.config.schema_ or "public"
        table_name = table.table

        table_rows = self._run_query(
            self.TABLE_SQL.format(project, dataset), {"table_name": table_name}
        )
        if not table_rows:
            return ChangeSummary()

        record = table_rows[0]
        snapshot_id = str(record.get("last_modified_time"))
        changed_partitions: List[str] = []

        if previous_snapshot_id:
            partition_rows = self._run_query(
                self.PARTITION_SQL.format(project, dataset),
                {
                    "table_name": table_name,
                    "threshold": previous_snapshot_id,
                    "limit": self.config.partial_profiling.max_partitions_per_run,
                },
            )
            changed_partitions = [row["partition_id"] for row in partition_rows]

        return ChangeSummary(
            snapshot_id=snapshot_id,
            row_count=record.get("row_count"),
            changed_partitions=changed_partitions,
            metadata={
                "last_modified_time": snapshot_id,
                "row_count": record.get("row_count"),
                "changed_partition_count": len(changed_partitions),
            },
        )


DETECTOR_REGISTRY: Dict[str, Type[ChangeDetector]] = {
    "postgres": PostgresChangeDetector,
    "snowflake": SnowflakeChangeDetector,
    "bigquery": BigQueryChangeDetector,
}


def build_change_detector(
    warehouse_type: str, connector: BaseConnector, config: IncrementalConfig
) -> ChangeDetector:
    """Instantiate a change detector for the warehouse."""
    detector_cls = DETECTOR_REGISTRY.get(warehouse_type.lower(), NoopChangeDetector)
    return detector_cls(connector, config)

"""
Persistence layer for incremental profiling metadata.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
    update,
)
from sqlalchemy.sql import Insert, Update

from ..config.schema import StorageConfig
from ..connectors.factory import create_connector

logger = logging.getLogger(__name__)


@dataclass
class TableState:
    """Row stored in the incremental metadata table."""

    table_name: str
    schema_name: Optional[str] = None
    database_name: Optional[str] = None
    last_run_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    change_token: Optional[str] = None
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    last_profiled_at: Optional[datetime] = None
    staleness_score: Optional[int] = None
    row_count: Optional[int] = None
    bytes_scanned: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def table_key(self) -> str:
        """Get unique table key including database, schema, and table name."""
        parts = []
        if self.database_name:
            parts.append(self.database_name)
        if self.schema_name:
            parts.append(self.schema_name)
        parts.append(self.table_name)
        return ".".join(parts)


class TableStateStore:
    """CRUD wrapper around the metadata table used by the incremental planner."""

    def __init__(
        self,
        storage_config: StorageConfig,
        table_name: str,
        retry_config=None,
        create_tables: bool = True,
    ):
        self.config = storage_config
        self.table_name = table_name
        connector = create_connector(storage_config.connection, retry_config)
        self.engine = connector.engine
        self._metadata = MetaData()
        self._table = Table(
            self.table_name,
            self._metadata,
            Column("database_name", String(255), primary_key=True, nullable=True),
            Column("schema_name", String(255), primary_key=True, nullable=True),
            Column("table_name", String(255), primary_key=True, nullable=False),
            Column("last_run_id", String(36)),
            Column("snapshot_id", String(255)),
            Column("change_token", String(255)),
            Column("decision", String(50)),
            Column("decision_reason", String(255)),
            Column("last_profiled_at", DateTime),
            Column("staleness_score", Integer),
            Column("row_count", BigInteger),
            Column("bytes_scanned", BigInteger),
            Column("metadata", Text),
            extend_existing=True,
        )
        if create_tables and storage_config.create_tables:
            self._metadata.create_all(self.engine)
            logger.debug("Ensured incremental state table %s exists", self.table_name)

    def load_state(
        self, table_name: str, schema_name: Optional[str], database_name: Optional[str] = None
    ) -> Optional[TableState]:
        with self.engine.connect() as conn:
            schema_clause = (
                self._table.c.schema_name.is_(None)
                if schema_name is None
                else self._table.c.schema_name == schema_name
            )
            database_clause = (
                self._table.c.database_name.is_(None)
                if database_name is None
                else self._table.c.database_name == database_name
            )
            stmt = (
                select(self._table)
                .where(self._table.c.table_name == table_name)
                .where(schema_clause)
                .where(database_clause)
                .limit(1)
            )
            row = conn.execute(stmt).fetchone()
            if not row:
                return None
            data = dict(row._mapping)
            metadata_blob = data.get("metadata")
            metadata = json.loads(metadata_blob) if metadata_blob else {}
            return TableState(
                table_name=data["table_name"],
                schema_name=data.get("schema_name"),
                database_name=data.get("database_name"),
                last_run_id=data.get("last_run_id"),
                snapshot_id=data.get("snapshot_id"),
                change_token=data.get("change_token"),
                decision=data.get("decision"),
                decision_reason=data.get("decision_reason"),
                last_profiled_at=data.get("last_profiled_at"),
                staleness_score=data.get("staleness_score"),
                row_count=data.get("row_count"),
                bytes_scanned=data.get("bytes_scanned"),
                metadata=metadata,
            )

    def upsert_state(self, state: TableState):
        payload = {
            "database_name": state.database_name,
            "schema_name": state.schema_name,
            "table_name": state.table_name,
            "last_run_id": state.last_run_id,
            "snapshot_id": state.snapshot_id,
            "change_token": state.change_token,
            "decision": state.decision,
            "decision_reason": state.decision_reason,
            "last_profiled_at": state.last_profiled_at,
            "staleness_score": state.staleness_score,
            "row_count": state.row_count,
            "bytes_scanned": state.bytes_scanned,
            "metadata": json.dumps(state.metadata or {}),
        }
        existing = self.load_state(state.table_name, state.schema_name, state.database_name)
        schema_clause = (
            self._table.c.schema_name.is_(None)
            if state.schema_name is None
            else self._table.c.schema_name == state.schema_name
        )
        database_clause = (
            self._table.c.database_name.is_(None)
            if state.database_name is None
            else self._table.c.database_name == state.database_name
        )
        with self.engine.begin() as conn:
            if existing:
                stmt: Update = (
                    update(self._table)
                    .where(self._table.c.table_name == state.table_name)
                    .where(schema_clause)
                    .where(database_clause)
                    .values(**payload)
                )
                conn.execute(stmt)
            else:
                stmt_insert: Insert = insert(self._table).values(**payload)
                conn.execute(stmt_insert)

    def record_decision(
        self,
        table_name: str,
        schema_name: Optional[str],
        decision: str,
        reason: str,
        snapshot_id: Optional[str],
        database_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        state = self.load_state(table_name, schema_name, database_name) or TableState(
            table_name=table_name,
            schema_name=schema_name,
            database_name=database_name,
        )
        state.decision = decision
        state.decision_reason = reason
        state.snapshot_id = snapshot_id or state.snapshot_id
        state.metadata = metadata or state.metadata
        state.last_profiled_at = datetime.utcnow()
        self.upsert_state(state)

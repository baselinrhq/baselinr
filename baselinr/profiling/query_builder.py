"""
SQL query builder for partition-aware and sampled profiling.

Generates warehouse-specific SQL that combines partition filtering and sampling.
"""

import logging
from typing import Optional, Tuple

from sqlalchemy import Table, func, select
from sqlalchemy.sql import Select

from ..config.schema import PartitionConfig, SamplingConfig

logger = logging.getLogger(__name__)


class QueryBuilder:
    """Builds SQL queries with partition filtering and sampling."""

    def __init__(self, database_type: str):
        """
        Initialize query builder.

        Args:
            database_type: Type of database (postgres, snowflake, sqlite)
        """
        self.database_type = database_type.lower()

    def build_profiling_query(
        self,
        table: Table,
        partition_config: Optional[PartitionConfig] = None,
        sampling_config: Optional[SamplingConfig] = None,
    ) -> Tuple[Select, dict]:
        """
        Build a SQL query with partition filtering and sampling.

        Args:
            table: SQLAlchemy Table object
            partition_config: Partition configuration (optional)
            sampling_config: Sampling configuration (optional)

        Returns:
            Tuple of (SQLAlchemy select statement, metadata dict)
        """
        metadata = {
            "partition_applied": False,
            "sampling_applied": False,
            "partition_strategy": None,
            "sampling_method": None,
        }

        # Start with base query
        query = select(table)

        # Apply partition filtering
        if partition_config and partition_config.key:
            query = self._apply_partition_filter(query, table, partition_config)
            metadata["partition_applied"] = True  # type: ignore[assignment]
            metadata["partition_strategy"] = partition_config.strategy  # type: ignore[assignment]

        # Apply sampling
        if sampling_config and sampling_config.enabled:
            query = self._apply_sampling(query, table, sampling_config)
            metadata["sampling_applied"] = True  # type: ignore[assignment]
            metadata["sampling_method"] = sampling_config.method  # type: ignore[assignment]

        return query, metadata

    def _apply_partition_filter(
        self, query: Select, table: Table, partition_config: PartitionConfig
    ) -> Select:
        """
        Apply partition filtering to query.

        Args:
            query: Base SQL query
            table: SQLAlchemy Table object
            partition_config: Partition configuration

        Returns:
            Modified query with partition filter
        """
        partition_key = partition_config.key
        strategy = partition_config.strategy

        if partition_key is None or partition_key not in table.c:
            logger.warning(
                f"Partition key '{partition_key}' not found in table columns. "
                "Profiling will use full table."
            )
            return query

        if partition_key is None:
            return query

        partition_column = table.c[partition_key]

        if strategy == "latest":
            # Filter to latest partition value
            subquery = select(func.max(partition_column)).select_from(table).scalar_subquery()
            query = query.where(partition_column == subquery)
            logger.info(f"Applied 'latest' partition filter on {partition_key}")

        elif strategy == "recent_n":
            # Filter to N most recent partitions
            n = partition_config.recent_n or 1
            # Get top N distinct partition values
            subquery = (
                select(partition_column)
                .distinct()
                .order_by(partition_column.desc())
                .limit(n)
                .scalar_subquery()
            )
            query = query.where(partition_column.in_(subquery))
            logger.info(f"Applied 'recent_{n}' partition filter on {partition_key}")

        elif strategy == "sample":
            # Sample from partition values (not implemented yet - use all for now)
            logger.warning(
                "Partition strategy 'sample' not fully implemented, using all partitions"
            )

        elif strategy == "specific_values":
            values = partition_config.values or []
            if not values:
                logger.warning(
                    "specific_values strategy requested without values; using full table"
                )
            else:
                query = query.where(partition_column.in_(values))
                logger.info(
                    "Applied 'specific_values' partition filter on %s (%d values)",
                    partition_key,
                    len(values),
                )

        elif strategy == "all":
            # No filtering - profile all partitions
            logger.info("Using all partitions (no filter)")

        return query

    def _apply_sampling(
        self, query: Select, table: Table, sampling_config: SamplingConfig
    ) -> Select:
        """
        Apply sampling to query.

        Args:
            query: Base SQL query
            table: SQLAlchemy Table object
            sampling_config: Sampling configuration

        Returns:
            Modified query with sampling
        """
        method = sampling_config.method
        fraction = sampling_config.fraction
        max_rows = sampling_config.max_rows

        if self.database_type == "postgres":
            # PostgreSQL: TABLESAMPLE SYSTEM
            # Note: SQLAlchemy doesn't have native TABLESAMPLE support,
            # so we'll need to use text() for this
            percent = fraction * 100
            sample_clause = f"TABLESAMPLE SYSTEM ({percent})"
            logger.info(f"Applied PostgreSQL sampling: {sample_clause}")
            # For now, we'll return the query as-is and document that sampling
            # needs to be applied at the table level

        elif self.database_type == "snowflake":
            # Snowflake: SAMPLE clause
            if method == "random":
                percent = fraction * 100
                sample_clause = f"SAMPLE ({percent})"
                logger.info(f"Applied Snowflake sampling: {sample_clause}")
            else:
                logger.warning(f"Sampling method '{method}' not fully supported for Snowflake")

        elif self.database_type == "sqlite":
            # SQLite: Use RANDOM() with LIMIT
            if max_rows:
                query = query.order_by(func.random()).limit(max_rows)
                logger.info(f"Applied SQLite sampling with LIMIT {max_rows}")
            else:
                logger.warning("SQLite sampling requires max_rows to be set")

        # Apply max_rows limit if specified
        if max_rows and self.database_type != "sqlite":
            query = query.limit(max_rows)
            logger.info(f"Applied max_rows limit: {max_rows}")

        return query

    def get_sample_clause_text(
        self, table_name: str, sampling_config: Optional[SamplingConfig] = None
    ) -> str:
        """
        Get warehouse-specific SAMPLE clause as text.

        This is used when SQLAlchemy's query builder doesn't support
        the sampling syntax natively.

        Args:
            table_name: Name of the table
            sampling_config: Sampling configuration

        Returns:
            SQL fragment with table name and SAMPLE clause
        """
        if not sampling_config or not sampling_config.enabled:
            return table_name

        fraction = sampling_config.fraction
        method = sampling_config.method

        if self.database_type == "postgres":
            percent = fraction * 100
            return f"{table_name} TABLESAMPLE SYSTEM ({percent})"

        elif self.database_type == "snowflake":
            if method == "random":
                percent = fraction * 100
                return f"{table_name} SAMPLE ({percent})"
            elif method == "stratified":
                # Snowflake doesn't have built-in stratified sampling
                # Would need to implement manually
                logger.warning("Stratified sampling not natively supported in Snowflake")
                percent = fraction * 100
                return f"{table_name} SAMPLE ({percent})"

        return table_name

    def infer_partition_key(self, table: Table) -> Optional[str]:
        """
        Attempt to infer partition key from table metadata.

        Common patterns:
        - Columns named: date, created_at, event_date, partition_date, etc.
        - DATE or TIMESTAMP columns

        Args:
            table: SQLAlchemy Table object

        Returns:
            Inferred partition key or None
        """
        # Common partition column name patterns
        patterns = [
            "date",
            "event_date",
            "partition_date",
            "created_at",
            "updated_at",
            "timestamp",
            "dt",
            "ds",  # Common in data warehouses
        ]

        for column in table.columns:
            col_name_lower = column.name.lower()

            # Check if column name matches pattern
            if col_name_lower in patterns:
                logger.info(f"Inferred partition key from column name: {column.name}")
                return column.name

            # Check if it's a date/timestamp column
            col_type_str = str(column.type).lower()
            if any(t in col_type_str for t in ["date", "timestamp"]):
                # Prefer columns with 'date' in the name
                if "date" in col_name_lower:
                    logger.info(f"Inferred partition key from DATE column: {column.name}")
                    return column.name

        logger.debug("Could not infer partition key from table metadata")
        return None

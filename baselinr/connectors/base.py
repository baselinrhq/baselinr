"""
Base connector interface for Baselinr.

Defines the abstract interface that all database connectors must implement.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import MetaData, Table, inspect
from sqlalchemy.engine import Engine

from ..config.schema import ConnectionConfig

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Abstract base class for database connectors."""

    def __init__(self, config: ConnectionConfig, retry_config=None, execution_config=None):
        """
        Initialize connector with configuration.

        Args:
            config: Connection configuration
            retry_config: Optional retry configuration (RetryConfig object)
            execution_config: Optional execution configuration (ExecutionConfig object)
        """
        self.config = config
        self.retry_config = retry_config
        self.execution_config = execution_config
        self._engine: Optional[Engine] = None
        self._metadata: Optional[MetaData] = None

    @property
    def engine(self) -> Engine:
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    @property
    def metadata(self) -> MetaData:
        """Get or create SQLAlchemy metadata."""
        if self._metadata is None:
            self._metadata = MetaData()
            self._metadata.reflect(bind=self.engine)
        return self._metadata

    @abstractmethod
    def _create_engine(self) -> Engine:
        """
        Create SQLAlchemy engine for this connector type.

        Returns:
            Configured SQLAlchemy engine
        """
        pass

    def _get_pool_config(self) -> Dict[str, int]:
        """
        Calculate pool configuration based on execution settings.
        Only adjusts pool size when parallelism is enabled (max_workers > 1).

        Returns:
            Dictionary with pool_size and max_overflow
        """
        if self.execution_config and self.execution_config.max_workers > 1:
            max_workers = self.execution_config.max_workers
            # Set pool size based on worker count
            pool_size = min(max_workers + 2, 20)  # Cap at 20
            max_overflow = max_workers
        else:
            # Default pool size for sequential execution
            pool_size = 5
            max_overflow = 10

        return {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_pre_ping": True,  # Verify connections before use
        }

    @abstractmethod
    def get_connection_string(self) -> str:
        """
        Build database connection string.

        Returns:
            SQLAlchemy-compatible connection string
        """
        pass

    def _wrap_with_retry(self, func, *args, **kwargs):
        """
        Wrap a function with retry logic if retry is enabled.

        Args:
            func: Function to wrap
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func
        """
        if not self.retry_config or not self.retry_config.enabled:
            # Retry disabled, execute directly
            return func(*args, **kwargs)

        try:
            from ..utils.retry import (
                TransientWarehouseError,
                classify_database_error,
                retry_with_backoff,
            )

            # Apply retry decorator
            @retry_with_backoff(
                retries=self.retry_config.retries,
                backoff_strategy=self.retry_config.backoff_strategy,
                min_backoff=self.retry_config.min_backoff,
                max_backoff=self.retry_config.max_backoff,
                retry_on=(TransientWarehouseError,),
            )
            def wrapped_func():
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Classify the error and re-raise as transient or permanent
                    # Don't use 'from e' to avoid DBAPIError reconstruction issues
                    # The original exception is already stored in
                    # classified_error.original_exception
                    classified_error = classify_database_error(e)
                    raise classified_error

            return wrapped_func()
        except ImportError:
            # Retry module not available, execute directly
            logger.warning("Retry module not available, executing without retry")
            return func(*args, **kwargs)

    def list_schemas(self) -> List[str]:
        """
        List all available schemas in the database.

        Returns:
            List of schema names
        """

        def _list_schemas():
            inspector = inspect(self.engine)
            return inspector.get_schema_names()

        return cast(List[str], self._wrap_with_retry(_list_schemas))

    def list_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        List all tables in a schema.

        Args:
            schema: Schema name (None for default)

        Returns:
            List of table names
        """

        def _list_tables():
            inspector = inspect(self.engine)
            return inspector.get_table_names(schema=schema)

        return cast(List[str], self._wrap_with_retry(_list_tables))

    def get_table(self, table_name: str, schema: Optional[str] = None) -> Table:
        """
        Get SQLAlchemy Table object with reflected metadata.

        Args:
            table_name: Name of the table
            schema: Schema name (None for default)

        Returns:
            SQLAlchemy Table object
        """

        def _get_table():
            try:
                return Table(table_name, MetaData(), autoload_with=self.engine, schema=schema)
            except Exception as e:
                # Preserve original exception details
                fq_name = f"{schema}.{table_name}" if schema else table_name
                error_msg = str(e) if e else "Unknown error"
                error_type = type(e).__name__

                # If error message is just the table name, provide more context
                if error_msg == table_name or error_msg == fq_name:
                    error_msg = (
                        f"Table/view '{fq_name}' not found or cannot be reflected. "
                        f"Original error type: {error_type}"
                    )
                else:
                    error_msg = (
                        f"Failed to reflect table/view '{fq_name}': "
                        f"{error_msg} (type: {error_type})"
                    )

                # Re-raise with more context, preserving original exception type
                raise type(e)(error_msg).with_traceback(e.__traceback__) from e

        return cast(Table, self._wrap_with_retry(_get_table))

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results.

        Args:
            query: SQL query string

        Returns:
            List of result rows as dictionaries
        """

        def _execute_query():
            import time

            from ..utils.logging import get_logger, log_event

            # Get logger - use existing logger or create one
            try:
                query_logger = get_logger(__name__)
            except Exception:
                query_logger = logger

            # Truncate query for logging if too long
            query_preview = query[:200] + "..." if len(query) > 200 else query

            start_time = time.time()
            log_event(
                query_logger,
                "query_started",
                f"Executing query: {query_preview}",
                metadata={"query_length": len(query)},
            )

            try:
                with self.engine.connect() as conn:
                    result = conn.execute(query)
                    rows = [dict(row) for row in result]
                    duration = time.time() - start_time

                    # Record metrics: query completed
                    try:
                        from ..utils.metrics import (
                            get_warehouse_type,
                            is_metrics_enabled,
                            record_query_completed,
                        )

                        if is_metrics_enabled():
                            warehouse = get_warehouse_type(self.config)
                            record_query_completed(warehouse, duration)
                    except Exception:
                        pass  # Metrics optional

                    log_event(
                        query_logger,
                        "query_completed",
                        f"Query completed: {len(rows)} rows in {duration:.2f}s",
                        metadata={
                            "row_count": len(rows),
                            "duration_seconds": duration,
                            "query_preview": query_preview,
                        },
                    )

                    return rows
            except Exception as e:
                duration = time.time() - start_time

                # Safely extract error type name without accessing exception internals
                try:
                    error_type_name = type(e).__name__
                except Exception:
                    error_type_name = "Exception"

                error_str = str(e)

                # Record metrics: error
                try:
                    from ..utils.metrics import get_warehouse_type, is_metrics_enabled, record_error

                    if is_metrics_enabled():
                        warehouse = get_warehouse_type(self.config)
                        record_error(warehouse, error_type_name, "connector")
                except Exception:
                    pass  # Metrics optional

                log_event(
                    query_logger,
                    "query_failed",
                    f"Query failed after {duration:.2f}s: {error_str}",
                    level="error",
                    metadata={
                        "error": error_str,
                        "error_type": error_type_name,
                        "duration_seconds": duration,
                        "query_preview": query_preview,
                    },
                )
                raise

        return cast(List[Dict[str, Any]], self._wrap_with_retry(_execute_query))

    def close(self):
        """Close database connection."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._metadata = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

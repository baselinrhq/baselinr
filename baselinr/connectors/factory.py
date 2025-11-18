"""
Connector factory utilities for Baselinr.

Provides a single entrypoint for creating connectors based on the configured
source/warehouse. Centralising connector creation keeps retry/execution
settings consistent across the CLI, planner, and writer.
"""

from typing import Optional

from ..config.schema import ConnectionConfig, ExecutionConfig, RetryConfig
from . import (
    BaseConnector,
    BigQueryConnector,
    MySQLConnector,
    PostgresConnector,
    RedshiftConnector,
    SnowflakeConnector,
    SQLiteConnector,
)


def create_connector(
    connection: ConnectionConfig,
    retry_config: Optional[RetryConfig] = None,
    execution_config: Optional[ExecutionConfig] = None,
) -> BaseConnector:
    """
    Create a connector instance for the given connection configuration.

    Args:
        connection: Connection configuration block.
        retry_config: Optional retry configuration.
        execution_config: Optional execution configuration (for pool sizing).

    Returns:
        Instantiated connector.

    Raises:
        ValueError: If the connection type is not supported.
    """
    connection_type = connection.type

    if connection_type == "postgres":
        return PostgresConnector(connection, retry_config, execution_config)
    if connection_type == "snowflake":
        return SnowflakeConnector(connection, retry_config, execution_config)
    if connection_type == "sqlite":
        return SQLiteConnector(connection, retry_config, execution_config)
    if connection_type == "mysql":
        return MySQLConnector(connection, retry_config, execution_config)
    if connection_type == "bigquery":
        return BigQueryConnector(connection, retry_config, execution_config)
    if connection_type == "redshift":
        return RedshiftConnector(connection, retry_config, execution_config)

    raise ValueError(f"Unsupported connection type: {connection_type}")

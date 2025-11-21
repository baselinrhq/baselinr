"""Configuration builder for dashboard database connection."""

import logging

from ..config.schema import BaselinrConfig, DatabaseType

logger = logging.getLogger(__name__)


def build_connection_string(config: BaselinrConfig) -> str:
    """
    Build PostgreSQL connection string from BaselinrConfig.

    The dashboard currently only supports PostgreSQL and SQLite, so we convert
    the storage connection config to a connection string.

    Args:
        config: Baselinr configuration

    Returns:
        PostgreSQL or SQLite connection string

    Raises:
        ValueError: If the configured database type is not PostgreSQL or SQLite.
    """
    conn_config = config.storage.connection
    conn_type = conn_config.type

    if conn_type == DatabaseType.POSTGRES:
        host = conn_config.host or "localhost"
        port = conn_config.port or 5432
        username = conn_config.username or "baselinr"
        password = conn_config.password or ""
        database = conn_config.database

        if password:
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"postgresql://{username}@{host}:{port}/{database}"
    elif conn_type == DatabaseType.SQLITE:
        filepath = conn_config.filepath
        if not filepath:
            raise ValueError("SQLite connection requires 'filepath' to be specified.")
        return f"sqlite:///{filepath}"
    else:
        raise ValueError(
            f"Dashboard currently only supports PostgreSQL or SQLite. "
            f"Configured type: {conn_type.value}"
        )

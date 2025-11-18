"""PostgreSQL connector implementation."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .base import BaseConnector

logger = logging.getLogger(__name__)


class PostgresConnector(BaseConnector):
    """PostgreSQL database connector."""

    def _create_engine(self) -> Engine:
        """Create PostgreSQL engine with appropriate pool configuration."""
        connection_string = self.get_connection_string()
        logger.info(f"Connecting to PostgreSQL: {self.config.database}")

        # Get pool configuration based on execution settings
        pool_config = self._get_pool_config()

        # Merge pool config with extra params
        engine_params = {**pool_config, **self.config.extra_params}

        return create_engine(connection_string, **engine_params)

    def get_connection_string(self) -> str:
        """
        Build PostgreSQL connection string.

        Returns:
            PostgreSQL connection string
        """
        host = self.config.host or "localhost"
        port = self.config.port or 5432
        username = self.config.username or "postgres"
        password = self.config.password or ""
        database = self.config.database

        if password:
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"postgresql://{username}@{host}:{port}/{database}"

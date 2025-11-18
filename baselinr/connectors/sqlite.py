"""SQLite connector implementation."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .base import BaseConnector

logger = logging.getLogger(__name__)


class SQLiteConnector(BaseConnector):
    """SQLite database connector."""

    def _create_engine(self) -> Engine:
        """Create SQLite engine."""
        connection_string = self.get_connection_string()
        logger.info(f"Connecting to SQLite: {self.config.filepath or self.config.database}")

        return create_engine(connection_string, **self.config.extra_params)

    def get_connection_string(self) -> str:
        """
        Build SQLite connection string.

        Returns:
            SQLite connection string
        """
        filepath = self.config.filepath or self.config.database
        return f"sqlite:///{filepath}"

"""MySQL connector implementation."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .base import BaseConnector

logger = logging.getLogger(__name__)


class MySQLConnector(BaseConnector):
    """MySQL database connector."""

    def _create_engine(self) -> Engine:
        """Create MySQL engine."""
        connection_string = self.get_connection_string()
        logger.info(f"Connecting to MySQL: {self.config.database}")

        return create_engine(connection_string, **self.config.extra_params)

    def get_connection_string(self) -> str:
        """
        Build MySQL connection string.

        Returns:
            MySQL connection string
        """
        host = self.config.host or "localhost"
        port = self.config.port or 3306
        username = self.config.username or "root"
        password = self.config.password or ""
        database = self.config.database

        if password:
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"mysql+pymysql://{username}@{host}:{port}/{database}"

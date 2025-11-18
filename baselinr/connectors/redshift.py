"""Amazon Redshift connector implementation."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .base import BaseConnector

logger = logging.getLogger(__name__)


class RedshiftConnector(BaseConnector):
    """Amazon Redshift database connector."""

    def _create_engine(self) -> Engine:
        """Create Redshift engine."""
        connection_string = self.get_connection_string()
        logger.info(f"Connecting to Redshift: {self.config.database}")

        return create_engine(connection_string, **self.config.extra_params)

    def get_connection_string(self) -> str:
        """
        Build Redshift connection string.

        Returns:
            Redshift connection string
        """
        host = self.config.host
        port = self.config.port or 5439
        username = self.config.username
        password = self.config.password or ""
        database = self.config.database

        if not host:
            raise ValueError("Redshift requires a host (cluster endpoint)")
        if not username:
            raise ValueError("Redshift requires a username")

        # Redshift uses PostgreSQL protocol, so we use postgresql://
        # but with redshift+psycopg2 driver
        if password:
            return f"redshift+psycopg2://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"redshift+psycopg2://{username}@{host}:{port}/{database}"

"""Snowflake connector implementation."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .base import BaseConnector

logger = logging.getLogger(__name__)


class SnowflakeConnector(BaseConnector):
    """Snowflake database connector."""

    def _create_engine(self) -> Engine:
        """Create Snowflake engine."""
        connection_string = self.get_connection_string()
        logger.info(f"Connecting to Snowflake: {self.config.account}/{self.config.database}")

        return create_engine(connection_string, **self.config.extra_params)

    def get_connection_string(self) -> str:
        """
        Build Snowflake connection string.

        Returns:
            Snowflake connection string
        """
        username = self.config.username
        password = self.config.password
        account = self.config.account
        database = self.config.database
        warehouse = self.config.warehouse
        schema = self.config.schema_ or "PUBLIC"
        role = self.config.role

        # Build connection string
        conn_str = f"snowflake://{username}:{password}@{account}/{database}/{schema}"

        # Add parameters
        params = []
        if warehouse:
            params.append(f"warehouse={warehouse}")
        if role:
            params.append(f"role={role}")

        if params:
            conn_str += "?" + "&".join(params)

        return conn_str

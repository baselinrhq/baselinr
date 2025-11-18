"""BigQuery connector implementation."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .base import BaseConnector

logger = logging.getLogger(__name__)


class BigQueryConnector(BaseConnector):
    """Google BigQuery database connector."""

    def _create_engine(self) -> Engine:
        """Create BigQuery engine."""
        connection_string = self.get_connection_string()
        logger.info(f"Connecting to BigQuery: {self.config.database}")

        # BigQuery requires credentials_path or credentials_info
        extra_params = self.config.extra_params.copy()

        return create_engine(connection_string, **extra_params)

    def get_connection_string(self) -> str:
        """
        Build BigQuery connection string.

        Returns:
            BigQuery connection string
        """
        # BigQuery connection string format:
        # bigquery://project_id/dataset
        # or bigquery://project_id/dataset?credentials_path=/path/to/key.json

        project_id = self.config.database  # database field used for project_id
        dataset = self.config.schema_ or "default"  # schema field used for dataset

        conn_str = f"bigquery://{project_id}/{dataset}"

        # Add credentials if provided
        params = []
        credentials_path = self.config.extra_params.get("credentials_path")
        if credentials_path:
            params.append(f"credentials_path={credentials_path}")

        # Note: credentials_info (JSON string) should be passed via extra_params to create_engine
        # as it's not suitable for URL encoding

        if params:
            conn_str += "?" + "&".join(params)

        return conn_str

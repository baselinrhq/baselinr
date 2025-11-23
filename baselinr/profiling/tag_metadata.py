"""
Tag metadata provider system for Baselinr.

Supports reading tags from database-native sources (Snowflake object tags,
BigQuery labels, PostgreSQL/MySQL/Redshift comments) and external sources
(dbt manifest, custom metadata files).
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TagMetadataProvider(ABC):
    """Abstract base class for tag metadata providers."""

    @abstractmethod
    def get_table_tags(self, schema: str, table: str) -> List[str]:
        """
        Get tags for a specific table.

        Args:
            schema: Schema name
            table: Table name

        Returns:
            List of tag strings associated with the table
        """
        pass

    @abstractmethod
    def get_all_tagged_tables(self) -> Dict[str, List[str]]:
        """
        Get all tables with their tags.

        Returns:
            Dictionary mapping "schema.table" to list of tags
        """
        pass

    def filter_tables_by_tags(
        self,
        tables: List[tuple[str, Optional[str]]],
        required_tags: Optional[List[str]] = None,
        any_tags: Optional[List[str]] = None,
    ) -> List[tuple[str, Optional[str]]]:
        """
        Filter tables based on tag criteria.

        Args:
            tables: List of (table_name, schema_name) tuples
            required_tags: Tags that all must be present (AND logic)
            any_tags: Tags where any must be present (OR logic)

        Returns:
            Filtered list of (table_name, schema_name) tuples
        """
        if not required_tags and not any_tags:
            return tables

        tagged_tables = self.get_all_tagged_tables()
        filtered = []

        for table_name, schema_name in tables:
            full_name = f"{schema_name}.{table_name}" if schema_name else table_name
            table_tags = tagged_tables.get(full_name, [])

            # Check required tags (AND logic)
            if required_tags:
                if not all(tag in table_tags for tag in required_tags):
                    continue

            # Check any tags (OR logic)
            if any_tags:
                if not any(tag in table_tags for tag in any_tags):
                    continue

            filtered.append((table_name, schema_name))

        return filtered


class SnowflakeTagProvider(TagMetadataProvider):
    """Tag provider for Snowflake using ACCOUNT_USAGE.TAG_REFERENCES."""

    def __init__(self, connector):
        """
        Initialize Snowflake tag provider.

        Args:
            connector: SnowflakeConnector instance
        """
        self.connector = connector
        self._tag_cache: Optional[Dict[str, List[str]]] = None

    def get_table_tags(self, schema: str, table: str) -> List[str]:
        """Get tags for a specific table."""
        all_tags = self.get_all_tagged_tables()
        full_name = f"{schema}.{table}"
        return all_tags.get(full_name, [])

    def get_all_tagged_tables(self) -> Dict[str, List[str]]:
        """Get all tables with their tags from Snowflake ACCOUNT_USAGE."""
        if self._tag_cache is not None:
            return self._tag_cache

        try:
            query = """
                SELECT
                    OBJECT_SCHEMA || '.' || OBJECT_NAME as table_name,
                    TAG_NAME || ':' || TAG_VALUE as tag
                FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
                WHERE OBJECT_DOMAIN = 'TABLE'
                AND TAG_VALUE IS NOT NULL
                ORDER BY table_name, tag
            """

            results = self.connector.execute_query(query)
            tagged_tables: Dict[str, List[str]] = {}

            for row in results:
                table_name = row.get("table_name", "")
                tag = row.get("tag", "")

                if table_name and tag:
                    if table_name not in tagged_tables:
                        tagged_tables[table_name] = []
                    tagged_tables[table_name].append(tag)

            self._tag_cache = tagged_tables
            logger.debug(f"Loaded {len(tagged_tables)} tagged tables from Snowflake")
            return tagged_tables

        except Exception as e:
            logger.warning(f"Failed to load Snowflake tags: {e}")
            return {}


class BigQueryTagProvider(TagMetadataProvider):
    """Tag provider for BigQuery using table labels."""

    def __init__(self, connector):
        """
        Initialize BigQuery tag provider.

        Args:
            connector: BigQueryConnector instance
        """
        self.connector = connector
        self._tag_cache: Optional[Dict[str, List[str]]] = None

    def get_table_tags(self, schema: str, table: str) -> List[str]:
        """Get tags for a specific table."""
        all_tags = self.get_all_tagged_tables()
        full_name = f"{schema}.{table}"
        return all_tags.get(full_name, [])

    def get_all_tagged_tables(self) -> Dict[str, List[str]]:
        """Get all tables with their labels from BigQuery INFORMATION_SCHEMA."""
        if self._tag_cache is not None:
            return self._tag_cache

        try:
            # BigQuery stores labels in INFORMATION_SCHEMA.TABLE_OPTIONS
            # TODO: Implement BigQuery label retrieval when connector supports it
            # For now, return empty - will be implemented when we have BigQuery-specific access
            logger.warning("BigQuery label retrieval requires BigQuery-specific implementation")
            return {}

        except Exception as e:
            logger.warning(f"Failed to load BigQuery labels: {e}")
            return {}


class PostgresTagProvider(TagMetadataProvider):
    """Tag provider for PostgreSQL using comments/descriptions."""

    def __init__(self, connector):
        """
        Initialize PostgreSQL tag provider.

        Args:
            connector: PostgresConnector instance
        """
        self.connector = connector
        self._tag_cache: Optional[Dict[str, List[str]]] = None

    def get_table_tags(self, schema: str, table: str) -> List[str]:
        """Get tags for a specific table."""
        all_tags = self.get_all_tagged_tables()
        full_name = f"{schema}.{table}"
        return all_tags.get(full_name, [])

    def get_all_tagged_tables(self) -> Dict[str, List[str]]:
        """Get all tables with their tags from PostgreSQL comments."""
        if self._tag_cache is not None:
            return self._tag_cache

        try:
            # PostgreSQL stores comments in pg_description
            # Format: tags are comma-separated in comments
            query = """
                SELECT
                    n.nspname || '.' || c.relname as table_name,
                    COALESCE(d.description, '') as description
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = 0
                WHERE c.relkind IN ('r', 'v', 'm')
                  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                  AND d.description IS NOT NULL
                  AND d.description != ''
            """

            results = self.connector.execute_query(query)
            tagged_tables: Dict[str, List[str]] = {}

            for row in results:
                table_name = row.get("table_name", "")
                description = row.get("description", "")

                if table_name and description:
                    # Extract tags from description
                    # (assumes format like "tags: tag1, tag2" or just "tag1, tag2")
                    tags = self._parse_tags_from_description(description)
                    if tags:
                        tagged_tables[table_name] = tags

            self._tag_cache = tagged_tables
            logger.debug(f"Loaded {len(tagged_tables)} tagged tables from PostgreSQL")
            return tagged_tables

        except Exception as e:
            logger.warning(f"Failed to load PostgreSQL tags: {e}")
            return {}

    @staticmethod
    def _parse_tags_from_description(description: str) -> List[str]:
        """Parse tags from description text."""
        # Look for "tags:" prefix
        description_lower = description.lower()
        if "tags:" in description_lower:
            tag_part = description.split("tags:", 1)[1].strip()
        else:
            tag_part = description.strip()

        # Split by comma and clean
        tags = [tag.strip() for tag in tag_part.split(",") if tag.strip()]
        return tags


class MySQLTagProvider(TagMetadataProvider):
    """Tag provider for MySQL using table comments."""

    def __init__(self, connector):
        """
        Initialize MySQL tag provider.

        Args:
            connector: MySQLConnector instance
        """
        self.connector = connector
        self._tag_cache: Optional[Dict[str, List[str]]] = None

    def get_table_tags(self, schema: str, table: str) -> List[str]:
        """Get tags for a specific table."""
        all_tags = self.get_all_tagged_tables()
        full_name = f"{schema}.{table}"
        return all_tags.get(full_name, [])

    def get_all_tagged_tables(self) -> Dict[str, List[str]]:
        """Get all tables with their tags from MySQL INFORMATION_SCHEMA."""
        if self._tag_cache is not None:
            return self._tag_cache

        try:
            query = """
                SELECT
                    CONCAT(table_schema, '.', table_name) as table_name,
                    table_comment as comment
                FROM INFORMATION_SCHEMA.TABLES
                WHERE table_schema NOT IN (
                    'information_schema', 'performance_schema', 'mysql', 'sys'
                )
                AND table_comment IS NOT NULL
                AND table_comment != ''
            """

            results = self.connector.execute_query(query)
            tagged_tables: Dict[str, List[str]] = {}

            for row in results:
                table_name = row.get("table_name", "")
                comment = row.get("comment", "")

                if table_name and comment:
                    tags = PostgresTagProvider._parse_tags_from_description(comment)
                    if tags:
                        tagged_tables[table_name] = tags

            self._tag_cache = tagged_tables
            logger.debug(f"Loaded {len(tagged_tables)} tagged tables from MySQL")
            return tagged_tables

        except Exception as e:
            logger.warning(f"Failed to load MySQL tags: {e}")
            return {}


class RedshiftTagProvider(TagMetadataProvider):
    """Tag provider for Redshift using table comments (similar to PostgreSQL)."""

    def __init__(self, connector):
        """
        Initialize Redshift tag provider.

        Args:
            connector: RedshiftConnector instance
        """
        self.connector = connector
        self._tag_cache: Optional[Dict[str, List[str]]] = None

    def get_table_tags(self, schema: str, table: str) -> List[str]:
        """Get tags for a specific table."""
        all_tags = self.get_all_tagged_tables()
        full_name = f"{schema}.{table}"
        return all_tags.get(full_name, [])

    def get_all_tagged_tables(self) -> Dict[str, List[str]]:
        """Get all tables with their tags from Redshift comments."""
        # Redshift uses same pg_catalog as PostgreSQL
        # Use the same approach as PostgresTagProvider
        provider = PostgresTagProvider(self.connector)
        return provider.get_all_tagged_tables()


class SQLiteTagProvider(TagMetadataProvider):
    """Tag provider for SQLite (limited native support, uses external metadata)."""

    def __init__(self, connector, metadata_file: Optional[str] = None):
        """
        Initialize SQLite tag provider.

        Args:
            connector: SQLiteConnector instance
            metadata_file: Optional path to JSON file with tag metadata
        """
        self.connector = connector
        self.metadata_file = metadata_file
        self._tag_cache: Optional[Dict[str, List[str]]] = None

    def get_table_tags(self, schema: Optional[str], table: str) -> List[str]:
        """Get tags for a specific table."""
        all_tags = self.get_all_tagged_tables()
        full_name = f"{schema}.{table}" if schema else table
        return all_tags.get(full_name, [])

    def get_all_tagged_tables(self) -> Dict[str, List[str]]:
        """Get all tables with their tags from external metadata file."""
        if self._tag_cache is not None:
            return self._tag_cache

        if not self.metadata_file:
            logger.debug("No metadata file provided for SQLite tag provider")
            return {}

        try:
            import json
            from pathlib import Path

            metadata_path = Path(self.metadata_file)
            if not metadata_path.exists():
                logger.warning(f"Metadata file not found: {self.metadata_file}")
                return {}

            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Expected format: {"schema.table": ["tag1", "tag2"], ...}
            tagged_tables: Dict[str, List[str]] = {}
            for table_key, tags in metadata.items():
                if isinstance(tags, list):
                    tagged_tables[table_key] = tags
                elif isinstance(tags, str):
                    # Single tag as string
                    tagged_tables[table_key] = [tags]

            self._tag_cache = tagged_tables
            logger.debug(f"Loaded {len(tagged_tables)} tagged tables from SQLite metadata file")
            return tagged_tables

        except Exception as e:
            logger.warning(f"Failed to load SQLite tags from metadata file: {e}")
            return {}


class DBTTagProvider(TagMetadataProvider):
    """Tag provider for dbt projects (works with any database)."""

    def __init__(self, manifest_path: str):
        """
        Initialize dbt tag provider.

        Args:
            manifest_path: Path to dbt manifest.json file
        """
        self.manifest_path = manifest_path
        self._tag_cache: Optional[Dict[str, List[str]]] = None

    def get_table_tags(self, schema: str, table: str) -> List[str]:
        """Get tags for a specific table."""
        all_tags = self.get_all_tagged_tables()
        full_name = f"{schema}.{table}"
        return all_tags.get(full_name, [])

    def get_all_tagged_tables(self) -> Dict[str, List[str]]:
        """Get all tables with their tags from dbt manifest.json."""
        if self._tag_cache is not None:
            return self._tag_cache

        try:
            import json
            from pathlib import Path

            manifest_path = Path(self.manifest_path)
            if not manifest_path.exists():
                logger.warning(f"dbt manifest file not found: {self.manifest_path}")
                return {}

            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            tagged_tables: Dict[str, List[str]] = {}

            # dbt stores models in manifest["nodes"]
            nodes = manifest.get("nodes", {})
            for node_id, node in nodes.items():
                if node.get("resource_type") == "model":
                    # Get schema and table name
                    schema_name = node.get("schema", "")
                    table_name = node.get("alias", node.get("name", ""))
                    if schema_name and table_name:
                        full_name = f"{schema_name}.{table_name}"

                        # Get tags from node metadata
                        tags = node.get("tags", [])
                        if isinstance(tags, list):
                            tagged_tables[full_name] = tags

            self._tag_cache = tagged_tables
            logger.debug(f"Loaded {len(tagged_tables)} tagged tables from dbt manifest")
            return tagged_tables

        except Exception as e:
            logger.warning(f"Failed to load dbt tags from manifest: {e}")
            return {}


class TagResolver:
    """Resolves tags from appropriate provider based on connector type and config."""

    @staticmethod
    def create_provider(
        connector,
        config,
        tag_provider: Optional[str] = None,
        dbt_manifest_path: Optional[str] = None,
    ) -> Optional[TagMetadataProvider]:
        """
        Create appropriate tag provider based on connector type and config.

        Args:
            connector: Database connector instance
            config: ConnectionConfig instance
            tag_provider: Explicit provider name, or "auto" to auto-detect, or None to disable
            dbt_manifest_path: Path to dbt manifest.json if using dbt provider

        Returns:
            TagMetadataProvider instance or None if no suitable provider
        """
        if tag_provider is None:
            return None

        if tag_provider == "dbt":
            if not dbt_manifest_path:
                logger.warning("dbt tag provider requested but dbt_manifest_path not provided")
                return None
            return DBTTagProvider(dbt_manifest_path)

        if tag_provider == "auto":
            # Auto-detect based on connector type
            db_type = config.type.value if hasattr(config.type, "value") else str(config.type)

            if db_type == "snowflake":
                from ..connectors import SnowflakeConnector

                if isinstance(connector, SnowflakeConnector):
                    return SnowflakeTagProvider(connector)
            elif db_type == "bigquery":
                from ..connectors import BigQueryConnector

                if isinstance(connector, BigQueryConnector):
                    return BigQueryTagProvider(connector)
            elif db_type == "postgres":
                from ..connectors import PostgresConnector

                if isinstance(connector, PostgresConnector):
                    return PostgresTagProvider(connector)
            elif db_type == "mysql":
                from ..connectors import MySQLConnector

                if isinstance(connector, MySQLConnector):
                    return MySQLTagProvider(connector)
            elif db_type == "redshift":
                from ..connectors import RedshiftConnector

                if isinstance(connector, RedshiftConnector):
                    return RedshiftTagProvider(connector)
            elif db_type == "sqlite":
                from ..connectors import SQLiteConnector

                if isinstance(connector, SQLiteConnector):
                    return SQLiteTagProvider(connector)

            logger.warning(f"Auto-detect could not find suitable tag provider for {db_type}")
            return None

        # Explicit provider
        if tag_provider == "snowflake":
            return SnowflakeTagProvider(connector)
        elif tag_provider == "bigquery":
            return BigQueryTagProvider(connector)
        elif tag_provider == "postgres":
            return PostgresTagProvider(connector)
        elif tag_provider == "mysql":
            return MySQLTagProvider(connector)
        elif tag_provider == "redshift":
            return RedshiftTagProvider(connector)
        elif tag_provider == "sqlite":
            return SQLiteTagProvider(connector)
        else:
            logger.warning(f"Unknown tag provider: {tag_provider}")
            return None

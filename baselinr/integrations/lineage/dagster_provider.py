"""
Dagster lineage provider for Baselinr.

Extracts lineage from Dagster assets using multiple data sources:
- Metadata database (PostgreSQL/SQLite)
- Code scanning (Python files with @asset decorators)
- GraphQL API
"""

import ast
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import ColumnLineageEdge, LineageEdge, LineageProvider

# Optional Dagster integration
# Note: We don't actually need Dagster installed to read from the metadata database
# We only need SQLAlchemy to query the database tables
try:
    from dagster import AssetKey

    DAGSTER_AVAILABLE = True
except ImportError:
    DAGSTER_AVAILABLE = False
    # Type stubs for when Dagster is not available
    AssetKey = None  # type: ignore

# SQLAlchemy is always available (core dependency)
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


class DagsterLineageProvider(LineageProvider):
    """Lineage provider that extracts dependencies from Dagster assets."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Dagster lineage provider.

        Args:
            config: Optional configuration dictionary with:
                - metadata_db_url: PostgreSQL/SQLite connection string
                - code_locations: List of paths to scan for Dagster code
                - graphql_url: URL for Dagster GraphQL API
                - asset_table_mapping: Dict mapping AssetKey strings to (schema, table) tuples
                - auto_detect_metadata_db: Boolean to auto-detect from env vars
        """
        self.config = config or {}
        self.metadata_db_url = self.config.get("metadata_db_url")
        self.code_locations = self.config.get("code_locations", [])
        self.graphql_url = self.config.get("graphql_url")
        self.asset_table_mapping = self.config.get("asset_table_mapping", {})
        self.auto_detect_metadata_db = self.config.get("auto_detect_metadata_db", True)

        # Cache for extracted lineage
        self._asset_cache: Dict[str, Dict[str, Any]] = {}
        self._metadata_db_engine: Optional[Any] = None
        self._available_data_source: Optional[str] = None

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "dagster"

    def is_available(self) -> bool:
        """
        Check if Dagster provider is available.

        Returns:
            True if any data source is accessible
        """
        # Note: We don't require Dagster to be installed - we can read from
        # the metadata database directly using SQLAlchemy

        # Try to detect available data source
        if self._detect_available_data_source():
            return True

        return False

    def _detect_available_data_source(self) -> bool:
        """Detect which data source is available."""
        # Try metadata DB first
        if self._try_metadata_db():
            self._available_data_source = "metadata_db"
            return True

        # Try code scanning
        if self._try_code_scanning():
            self._available_data_source = "code"
            return True

        # Try GraphQL API
        if self._try_graphql_api():
            self._available_data_source = "graphql"
            return True

        return False

    def _try_metadata_db(self) -> bool:
        """Try to connect to metadata database."""
        # Note: We don't require Dagster to be installed - we just need database access
        # The metadata database can be queried directly with SQLAlchemy

        try:
            # Auto-detect from environment if enabled
            if self.auto_detect_metadata_db and not self.metadata_db_url:
                self.metadata_db_url = os.getenv("DAGSTER_POSTGRES_URL") or os.getenv(
                    "DAGSTER_SQLITE_PATH"
                )

            if not self.metadata_db_url:
                logger.debug("No Dagster metadata DB URL configured")
                return False

            logger.debug(f"Attempting to connect to Dagster metadata DB: {self.metadata_db_url}")

            # Try to create engine and query
            self._metadata_db_engine = create_engine(self.metadata_db_url)
            if not self._metadata_db_engine:
                logger.debug("Failed to create SQLAlchemy engine")
                return False

            with self._metadata_db_engine.connect() as conn:
                # Try to query asset_keys table (try both with and without schema)
                # Dagster tables are typically in public schema
                for table_name in ["public.asset_keys", "asset_keys"]:
                    try:
                        logger.debug(f"Trying to query table: {table_name}")
                        # Use autocommit to avoid transaction issues
                        result = (
                            conn.execution_options(autocommit=True)
                            .execute(text(f"SELECT COUNT(*) FROM {table_name} LIMIT 1"))
                            .fetchone()
                        )
                        if result:
                            logger.info(
                                f"Dagster metadata database accessible "
                                f"(found table: {table_name})"
                            )
                            return True
                    except Exception as table_error:
                        logger.debug(f"Table {table_name} not found or error: {table_error}")
                        # Rollback to clear any failed transaction
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        continue

            logger.warning(
                f"Could not find asset_keys table in Dagster metadata DB. "
                f"URL: {self.metadata_db_url}"
            )
        except Exception as e:
            logger.warning(
                f"Could not connect to Dagster metadata DB: {e}. " f"URL: {self.metadata_db_url}"
            )
            import traceback

            logger.debug(f"Full traceback: {traceback.format_exc()}")
            self._metadata_db_engine = None

        return False

    def _try_code_scanning(self) -> bool:
        """Try to scan code locations."""
        if not self.code_locations:
            return False

        for location in self.code_locations:
            if os.path.exists(location):
                logger.debug(f"Dagster code location accessible: {location}")
                return True

        return False

    def _try_graphql_api(self) -> bool:
        """Try to connect to GraphQL API."""
        if not self.graphql_url:
            return False

        try:
            import requests  # type: ignore[import-untyped]

            # Try a simple health check query
            response = requests.get(self.graphql_url.replace("/graphql", ""), timeout=2)
            if response.status_code == 200:
                logger.debug("Dagster GraphQL API accessible")
                return True
        except Exception as e:
            logger.debug(f"Could not connect to Dagster GraphQL API: {e}")

        return False

    def extract_lineage(self, table_name: str, schema: Optional[str] = None) -> List[LineageEdge]:
        """
        Extract lineage for a specific table from Dagster assets.

        Args:
            table_name: Name of the table
            schema: Optional schema name

        Returns:
            List of LineageEdge objects representing upstream dependencies
        """
        if not self.is_available():
            return []

        # Find asset that maps to this table
        asset_key = self._find_asset_for_table(table_name, schema)
        if not asset_key:
            table_id = f"{schema}.{table_name}" if schema else table_name
            logger.debug(f"Dagster provider: No asset found for table {table_id}")
            return []

        # Extract lineage based on available data source
        if self._available_data_source == "metadata_db":
            return self._extract_from_metadata_db(asset_key, table_name, schema)
        elif self._available_data_source == "code":
            return self._extract_from_code(asset_key, table_name, schema)
        elif self._available_data_source == "graphql":
            return self._extract_from_graphql(asset_key, table_name, schema)

        return []

    def _find_asset_for_table(self, table_name: str, schema: Optional[str] = None) -> Optional[str]:
        """
        Find Dagster AssetKey that maps to the given table.

        Returns:
            AssetKey string or None if not found
        """
        # Try explicit mapping first
        for asset_key_str, mapping in self.asset_table_mapping.items():
            if isinstance(mapping, (list, tuple)) and len(mapping) == 2:
                map_schema, map_table = mapping[0], mapping[1]
                if map_table == table_name and (schema is None or map_schema == schema):
                    return str(asset_key_str)

        # Try to find in cached assets
        for asset_key_str, asset_info in self._asset_cache.items():
            asset_schema, asset_table = self._map_asset_to_table(asset_key_str, asset_info)
            if asset_table == table_name and (schema is None or asset_schema == schema):
                return asset_key_str

        # Try to find in metadata database
        if self._metadata_db_engine:
            try:
                with self._metadata_db_engine.connect() as conn:
                    # Query asset_keys table to find matching asset
                    # Try both schemas (consistent with other queries)
                    result = None
                    for table_variant in ["public.asset_keys", "asset_keys"]:
                        try:
                            result = conn.execute(
                                text(f"SELECT asset_key FROM {table_variant}")
                            ).fetchall()
                            if result:
                                break
                        except Exception as e:
                            logger.debug(f"Error querying {table_variant}: {e}")
                            continue

                    if not result:
                        return None

                    for row in result:
                        asset_key_json: str = str(row[0])
                        try:
                            # Parse JSON format: '["baselinr_customer_analytics"]'
                            asset_key_parts = json.loads(asset_key_json)
                            if isinstance(asset_key_parts, list) and len(asset_key_parts) > 0:
                                asset_name = asset_key_parts[
                                    -1
                                ]  # Last part is usually the table name

                                # Try stripping "baselinr_" prefix first (most common case)
                                if asset_name.startswith("baselinr_"):
                                    stripped_name = asset_name[9:]
                                    if stripped_name == table_name:
                                        table_id = (
                                            f"{schema}.{table_name}" if schema else table_name
                                        )
                                        logger.debug(
                                            f"Found Dagster asset {asset_key_json} for table "
                                            f"{table_id}"
                                        )
                                        return asset_key_json

                                # Try exact match
                                if asset_name == table_name:
                                    table_id = f"{schema}.{table_name}" if schema else table_name
                                    logger.debug(
                                        f"Found Dagster asset {asset_key_json} for table "
                                        f"{table_id}"
                                    )
                                    return asset_key_json

                                # Try with schema prefix
                                if schema and asset_name == f"{schema}_{table_name}":
                                    table_id = f"{schema}.{table_name}"
                                    logger.debug(
                                        f"Found Dagster asset {asset_key_json} for table "
                                        f"{table_id}"
                                    )
                                    return asset_key_json
                        except (json.JSONDecodeError, IndexError) as e:
                            logger.debug(f"Error parsing asset key {asset_key_json}: {e}")
                            continue
            except Exception as e:
                table_id = f"{schema}.{table_name}" if schema else table_name
                logger.debug(f"Error querying asset_keys for table {table_id}: {e}")

        # No asset found - return None as documented
        return None

    def _map_asset_to_table(
        self, asset_key_str: str, asset_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Map Dagster AssetKey to database table.

        Args:
            asset_key_str: AssetKey as string (e.g., "schema::table" or
                '["baselinr_customer_analytics"]')
            asset_info: Optional asset metadata

        Returns:
            Tuple of (schema, table)
        """
        # Try metadata-based mapping
        if asset_info:
            metadata = asset_info.get("metadata", {})
            if "table" in metadata:
                table = metadata["table"]
                schema = metadata.get("schema", "public")
                return (schema, table)

        # Try parsing JSON format: '["baselinr_customer_analytics"]'
        try:
            asset_key_parts = json.loads(asset_key_str)
            if isinstance(asset_key_parts, list) and len(asset_key_parts) > 0:
                # If it has multiple parts, use last two as schema.table
                # Check this BEFORE prefix stripping to preserve schema info
                if len(asset_key_parts) >= 2:
                    schema_part = asset_key_parts[-2] or "public"
                    table_part = asset_key_parts[-1]
                    # Strip prefix from table part if present
                    if table_part.startswith("baselinr_"):
                        table_part = table_part[9:]
                    return (schema_part, table_part)

                # Single part: strip common prefixes like "baselinr_"
                asset_name = asset_key_parts[-1]
                if asset_name.startswith("baselinr_"):
                    table_name = asset_name[9:]
                    return ("public", table_name)
                return ("public", asset_name)
        except (json.JSONDecodeError, IndexError, AttributeError):
            pass

        # Try naming convention: AssetKey segments
        # Format: "schema::table" or ["schema", "table"]
        if "::" in asset_key_str:
            parts = asset_key_str.split("::")
            if len(parts) == 2:
                return (parts[0] or "public", parts[1])
            elif len(parts) > 2:
                # Multi-segment key, use last two
                return (parts[-2] or "public", parts[-1])

        # Default: assume asset key is table name
        return ("public", asset_key_str)

    def _extract_from_metadata_db(
        self, asset_key_str: str, table_name: str, schema: Optional[str] = None
    ) -> List[LineageEdge]:
        """Extract lineage from Dagster metadata database."""
        if not self._metadata_db_engine:
            return []

        try:
            edges: List[LineageEdge] = []
            with self._metadata_db_engine.connect() as conn:
                # Query for asset dependencies from event_logs table
                # Dagster stores events in event_logs (not event_log_entries)
                # Dependencies are typically in ASSET_MATERIALIZATION events
                result = None
                for table_variant in ["public.event_logs", "event_logs"]:
                    try:
                        # Parse asset_key_str if it's JSON
                        asset_key_for_query = asset_key_str
                        try:
                            asset_key_parts = json.loads(asset_key_str)
                            if isinstance(asset_key_parts, list):
                                asset_key_for_query = asset_key_str  # Use JSON string as-is
                        except (json.JSONDecodeError, AttributeError):
                            pass

                        query = text(
                            f"""
                            SELECT e.event, e.asset_key
                            FROM {table_variant} e
                            WHERE e.asset_key = :asset_key
                            AND e.dagster_event_type = 'ASSET_MATERIALIZATION'
                            ORDER BY e.id DESC
                            LIMIT 1
                            """
                        )
                        result = conn.execute(query, {"asset_key": asset_key_for_query}).fetchone()
                        if result:
                            break
                    except Exception as e:
                        logger.debug(f"Error querying {table_variant}: {e}")
                        continue

                if result and result[0]:
                    # Parse event JSON to extract dependencies
                    event_json = result[0]
                    try:
                        event_data = json.loads(event_json)
                        # Dependencies might be in event_specific_data.metadata or elsewhere
                        # For now, check if we can find them in the event structure
                        dependencies = self._extract_dependencies_from_event(event_data)

                        logger.debug(
                            f"Extracted {len(dependencies)} dependencies from "
                            f"materialization event for asset {asset_key_str}"
                        )

                        if dependencies:
                            downstream_schema, downstream_table = self._map_asset_to_table(
                                asset_key_str
                            )

                            for dep_asset_key in dependencies:
                                upstream_schema, upstream_table = self._map_asset_to_table(
                                    dep_asset_key
                                )

                                edge = LineageEdge(
                                    downstream_schema=downstream_schema,
                                    downstream_table=downstream_table,
                                    upstream_schema=upstream_schema,
                                    upstream_table=upstream_table,
                                    lineage_type="dagster_asset",
                                    provider="dagster",
                                    confidence_score=1.0,
                                    metadata={
                                        "asset_key": asset_key_str,
                                        "depends_on": dep_asset_key,
                                    },
                                )
                                edges.append(edge)
                        else:
                            table_id = f"{schema}.{table_name}" if schema else table_name
                            logger.debug(
                                f"No dependencies found in materialization event for asset "
                                f"{asset_key_str} (table {table_id})"
                            )
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug(f"Error parsing event JSON: {e}")

            if not edges:
                table_id = f"{schema}.{table_name}" if schema else table_name
                logger.debug(
                    f"No dependencies found in materialization event for asset {asset_key_str} "
                    f"(table {table_id})"
                )
            return edges
        except Exception as e:
            table_id = f"{schema}.{table_name}" if schema else table_name
            logger.debug(f"Error extracting Dagster lineage from metadata DB for {table_id}: {e}")
            return []

    def _extract_from_code(
        self, asset_key_str: str, table_name: str, schema: Optional[str] = None
    ) -> List[LineageEdge]:
        """Extract lineage from code scanning."""
        edges = []
        for location in self.code_locations:
            location_edges = self._scan_code_location(location, asset_key_str, table_name, schema)
            edges.extend(location_edges)

        return edges

    def _scan_code_location(
        self,
        location: str,
        asset_key_str: str,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[LineageEdge]:
        """Scan a code location for asset definitions."""
        edges: List[LineageEdge] = []
        path = Path(location)

        if not path.exists():
            return edges

        # Find all Python files
        python_files = list(path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Parse AST
                tree = ast.parse(content)

                # Find @asset decorators
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Check for @asset decorator
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Call):
                                if (
                                    isinstance(decorator.func, ast.Name)
                                    and decorator.func.id == "asset"
                                ):
                                    # Extract deps parameter
                                    deps = []
                                    for keyword in decorator.keywords:
                                        if keyword.arg == "deps":
                                            if isinstance(keyword.value, ast.List):
                                                deps = [
                                                    self._ast_to_asset_key(elem)
                                                    for elem in keyword.value.elts
                                                ]

                                    # Check if this asset matches our table
                                    asset_name = self._get_asset_name_from_node(node)
                                    if asset_name == asset_key_str or self._matches_table(
                                        asset_name, table_name, schema
                                    ):
                                        downstream_schema, downstream_table = (
                                            self._map_asset_to_table(asset_name)
                                        )

                                        for dep_asset_key in deps:
                                            upstream_schema, upstream_table = (
                                                self._map_asset_to_table(dep_asset_key)
                                            )

                                            edge = LineageEdge(
                                                downstream_schema=downstream_schema,
                                                downstream_table=downstream_table,
                                                upstream_schema=upstream_schema,
                                                upstream_table=upstream_table,
                                                lineage_type="dagster_asset",
                                                provider="dagster",
                                                confidence_score=0.9,
                                                metadata={
                                                    "asset_key": asset_name,
                                                    "depends_on": dep_asset_key,
                                                    "source_file": str(py_file),
                                                },
                                            )
                                            edges.append(edge)

            except Exception as e:
                logger.debug(f"Error scanning file {py_file}: {e}")

        return edges

    def _ast_to_asset_key(self, node: ast.AST) -> str:
        """Convert AST node to AssetKey string."""
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.List):
            # AssetKey(["schema", "table"])
            parts = [self._ast_to_asset_key(elem) for elem in node.elts]
            return "::".join(parts)
        elif isinstance(node, ast.Call):
            # AssetKey("table") or AssetKey(["schema", "table"])
            if isinstance(node.func, ast.Name) and node.func.id == "AssetKey":
                if node.args:
                    return self._ast_to_asset_key(node.args[0])
        return ""

    def _get_asset_name_from_node(self, node: ast.FunctionDef) -> str:
        """Get asset name from function node."""
        # Use function name as asset key
        return node.name

    def _matches_table(
        self, asset_key_str: str, table_name: str, schema: Optional[str] = None
    ) -> bool:
        """Check if asset key matches table."""
        asset_schema, asset_table = self._map_asset_to_table(asset_key_str)
        return asset_table == table_name and (schema is None or asset_schema == schema)

    def _asset_key_to_path(self, asset_key_str: str) -> List[str]:
        """
        Convert asset key string to path array for GraphQL API.

        Handles both formats:
        - JSON format: '["baselinr_customer_analytics"]' -> ['baselinr_customer_analytics']
        - :: format: 'schema::table' -> ['schema', 'table']

        Args:
            asset_key_str: Asset key as string

        Returns:
            List of path segments
        """
        # Try parsing as JSON first (most common from metadata DB)
        try:
            parsed = json.loads(asset_key_str)
            if isinstance(parsed, list):
                return [str(part) for part in parsed]
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

        # Fall back to :: format
        if "::" in asset_key_str:
            return asset_key_str.split("::")

        # Single segment (just table name)
        return [asset_key_str]

    def _extract_from_graphql(
        self, asset_key_str: str, table_name: str, schema: Optional[str] = None
    ) -> List[LineageEdge]:
        """Extract lineage from Dagster GraphQL API."""
        if not self.graphql_url:
            return []

        try:
            import requests  # type: ignore[import-untyped]

            # GraphQL query to get asset dependencies
            query = """
            query GetAssetDependencies($assetKey: AssetKeyInput!) {
                assetNodeOrError(assetKey: $assetKey) {
                    ... on AssetNode {
                        id
                        dependencies {
                            asset {
                                key {
                                    path
                                }
                            }
                        }
                    }
                }
            }
            """

            # Convert asset_key_str to path array for GraphQL
            # Handle both JSON format ('["baselinr_customer_analytics"]')
            # and :: format ('schema::table')
            asset_path = self._asset_key_to_path(asset_key_str)
            variables = {"assetKey": {"path": asset_path}}

            response = requests.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data and "assetNodeOrError" in data["data"]:
                    asset_node = data["data"]["assetNodeOrError"]
                    if "dependencies" in asset_node:
                        edges: List[LineageEdge] = []
                        downstream_schema, downstream_table = self._map_asset_to_table(
                            asset_key_str
                        )

                        for dep in asset_node["dependencies"]:
                            # Validate dependency structure before accessing
                            if (
                                not isinstance(dep, dict)
                                or "asset" not in dep
                                or "key" not in dep["asset"]
                                or "path" not in dep["asset"]["key"]
                            ):
                                logger.debug(
                                    "Skipping invalid dependency structure in GraphQL response"
                                )
                                continue

                            dep_path = dep["asset"]["key"]["path"]
                            if not dep_path or not isinstance(dep_path, list):
                                logger.debug("Skipping dependency with empty or invalid path")
                                continue

                            dep_asset_key = "::".join(dep_path)
                            upstream_schema, upstream_table = self._map_asset_to_table(
                                dep_asset_key
                            )

                            edge = LineageEdge(
                                downstream_schema=downstream_schema,
                                downstream_table=downstream_table,
                                upstream_schema=upstream_schema,
                                upstream_table=upstream_table,
                                lineage_type="dagster_asset",
                                provider="dagster",
                                confidence_score=1.0,
                                metadata={
                                    "asset_key": asset_key_str,
                                    "depends_on": dep_asset_key,
                                    "source": "graphql",
                                },
                            )
                            edges.append(edge)

                        return edges

        except Exception as e:
            table_id = f"{schema}.{table_name}" if schema else table_name
            logger.warning(f"Error extracting Dagster lineage from GraphQL API for {table_id}: {e}")

        return []

    def extract_column_lineage(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ColumnLineageEdge]:
        """
        Extract column-level lineage for a specific table from Dagster assets.

        Args:
            table_name: Name of the table
            schema: Optional schema name

        Returns:
            List of ColumnLineageEdge objects representing column dependencies
        """
        if not self.is_available():
            return []

        # Find asset that maps to this table
        asset_key = self._find_asset_for_table(table_name, schema)
        if not asset_key:
            table_id = f"{schema}.{table_name}" if schema else table_name
            logger.debug(f"Dagster provider: No asset found for column lineage of {table_id}")
            return []

        # Extract column lineage based on available data source
        if self._available_data_source == "metadata_db":
            return self._extract_column_lineage_from_metadata_db(asset_key, table_name, schema)
        elif self._available_data_source == "code":
            return self._extract_column_lineage_from_code(asset_key, table_name, schema)
        elif self._available_data_source == "graphql":
            return self._extract_column_lineage_from_graphql(asset_key, table_name, schema)

        return []

    def _extract_column_lineage_from_metadata_db(
        self, asset_key_str: str, table_name: str, schema: Optional[str] = None
    ) -> List[ColumnLineageEdge]:
        """Extract column lineage from metadata database."""
        if not self._metadata_db_engine:
            return []

        try:
            edges: List[ColumnLineageEdge] = []
            with self._metadata_db_engine.connect() as conn:
                # Query for latest materialization with column lineage metadata
                # Use event_logs table (not event_log_entries)
                result = None
                event_found = False
                for table_variant in ["public.event_logs", "event_logs"]:
                    try:
                        # Parse asset_key_str if it's JSON
                        asset_key_for_query = asset_key_str
                        try:
                            asset_key_parts = json.loads(asset_key_str)
                            if isinstance(asset_key_parts, list):
                                asset_key_for_query = asset_key_str  # Use JSON string as-is
                        except (json.JSONDecodeError, AttributeError):
                            pass

                        query = text(
                            f"""
                            SELECT e.event
                            FROM {table_variant} e
                            WHERE e.asset_key = :asset_key
                            AND e.dagster_event_type = 'ASSET_MATERIALIZATION'
                            ORDER BY e.id DESC
                            LIMIT 1
                            """
                        )
                        result = conn.execute(query, {"asset_key": asset_key_for_query}).fetchone()
                        if result:
                            event_found = True
                            break
                    except Exception as e:
                        logger.debug(f"Error querying {table_variant}: {e}")
                        continue

                if result and result[0]:
                    event_json = result[0]
                    try:
                        event_data = json.loads(event_json)
                        # Extract metadata from event
                        dagster_event = event_data.get("dagster_event", {})
                        event_specific_data = dagster_event.get("event_specific_data", {})
                        metadata = event_specific_data.get("metadata", {})

                        column_edges = self._extract_column_lineage_from_metadata(
                            metadata, asset_key_str
                        )
                        edges.extend(column_edges)
                        if not edges:
                            logger.debug(
                                f"Materialization event found for asset {asset_key_str}, "
                                f"but no column lineage metadata present"
                            )
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug(f"Error parsing event JSON for column lineage: {e}")

            if not event_found:
                table_id = f"{schema}.{table_name}" if schema else table_name
                logger.debug(
                    f"No materialization events found for asset {asset_key_str} "
                    f"(table {table_id})"
                )
            return edges
        except Exception as e:
            table_id = f"{schema}.{table_name}" if schema else table_name
            logger.debug(
                f"Error extracting Dagster column lineage from metadata DB for {table_id}: {e}"
            )
            return []

    def _extract_column_lineage_from_code(
        self, asset_key_str: str, table_name: str, schema: Optional[str] = None
    ) -> List[ColumnLineageEdge]:
        """Extract column lineage from code scanning."""
        edges = []
        for location in self.code_locations:
            location_edges = self._scan_code_for_column_lineage(
                location, asset_key_str, table_name, schema
            )
            edges.extend(location_edges)

        return edges

    def _scan_code_for_column_lineage(
        self,
        location: str,
        asset_key_str: str,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[ColumnLineageEdge]:
        """Scan code for column lineage metadata."""
        edges: List[ColumnLineageEdge] = []
        path = Path(location)

        if not path.exists():
            return edges

        python_files = list(path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Look for MaterializeResult with column lineage metadata
                if "dagster/column_lineage" in content or "TableColumnLineage" in content:
                    # For now, return empty - full implementation would parse the metadata
                    logger.debug(
                        f"Found column lineage metadata in {py_file}, "
                        "but full parsing not yet implemented"
                    )

            except Exception as e:
                logger.debug(f"Error scanning file {py_file} for column lineage: {e}")

        return edges

    def _extract_column_lineage_from_graphql(
        self, asset_key_str: str, table_name: str, schema: Optional[str] = None
    ) -> List[ColumnLineageEdge]:
        """Extract column lineage from GraphQL API."""
        # GraphQL API column lineage extraction would go here
        return []

    def _extract_dependencies_from_event(self, event_data: Dict[str, Any]) -> List[str]:
        """
        Extract asset dependencies from Dagster event JSON.

        Args:
            event_data: Parsed event JSON

        Returns:
            List of dependency asset key strings (in JSON format like '["asset_name"]')
        """
        dependencies = []
        try:
            # Try various paths where dependencies might be stored
            dagster_event = event_data.get("dagster_event", {})
            event_specific_data = dagster_event.get("event_specific_data", {})

            # Check asset_lineage first (most common location)
            asset_lineage = event_specific_data.get("asset_lineage", [])
            if asset_lineage and isinstance(asset_lineage, list):
                for lineage_item in asset_lineage:
                    # Lineage item might be an AssetKey object or dict
                    if isinstance(lineage_item, dict):
                        if "path" in lineage_item:
                            # Format as JSON string to match asset_key format
                            dep_key = json.dumps(lineage_item["path"])
                            dependencies.append(dep_key)
                        elif (
                            "__class__" in lineage_item
                            and "AssetKey" in lineage_item.get("__class__", "")
                            and "path" in lineage_item
                        ):
                            # AssetKey object with path (check path here since it's in elif)
                            dep_key = json.dumps(lineage_item["path"])
                            dependencies.append(dep_key)

            # Check metadata for dependencies
            metadata = event_specific_data.get("metadata", {})
            if "dagster/asset_dependencies" in metadata:
                deps_metadata = metadata["dagster/asset_dependencies"]
                if isinstance(deps_metadata, dict) and "value" in deps_metadata:
                    deps_value = deps_metadata["value"]
                    if isinstance(deps_value, list):
                        for dep in deps_value:
                            if isinstance(dep, (list, dict)):
                                dep_key = json.dumps(
                                    dep if isinstance(dep, list) else dep.get("path", [])
                                )
                                dependencies.append(dep_key)
                            else:
                                dependencies.append(str(dep))

            # Check for step_inputs which might contain dependencies
            step_inputs = event_specific_data.get("step_inputs", [])
            for step_input in step_inputs:
                if "asset_key" in step_input:
                    asset_key = step_input["asset_key"]
                    if isinstance(asset_key, dict) and "path" in asset_key:
                        dep_key = json.dumps(asset_key["path"])
                        dependencies.append(dep_key)
                    elif isinstance(asset_key, list):
                        dep_key = json.dumps(asset_key)
                        dependencies.append(dep_key)
        except (KeyError, TypeError, AttributeError) as e:
            logger.debug(f"Error extracting dependencies from event: {e}")

        return dependencies

    def _extract_column_lineage_from_metadata(
        self, metadata: Dict[str, Any], asset_key_str: str
    ) -> List[ColumnLineageEdge]:
        """
        Parse Dagster column lineage metadata.

        Expected format:
        {
            "dagster/column_lineage": {
                "deps_by_column": {
                    "output_col": [
                        {
                            "asset_key": {"path": ["schema", "table"]},
                            "column_name": "source_col"
                        }
                    ]
                }
            }
        }

        Args:
            metadata: Metadata dictionary from materialization event
            asset_key_str: Asset key string for the downstream asset
        """
        edges: List[ColumnLineageEdge] = []
        column_lineage_metadata = metadata.get("dagster/column_lineage")
        if not column_lineage_metadata or not isinstance(column_lineage_metadata, dict):
            return edges

        # Dagster metadata entries are wrapped in a "value" key
        # Check for the value wrapper (consistent with dependency extraction)
        if "value" in column_lineage_metadata:
            column_lineage = column_lineage_metadata["value"]
        else:
            # Fallback: assume the metadata is directly the column lineage data
            column_lineage = column_lineage_metadata

        if not isinstance(column_lineage, dict):
            return edges

        deps_by_column = column_lineage.get("deps_by_column", {})
        # Map the downstream asset key to table
        downstream_schema, downstream_table = self._map_asset_to_table(asset_key_str)

        for output_col, deps in deps_by_column.items():
            # Validate deps is iterable (list)
            if not isinstance(deps, list):
                logger.debug(
                    f"Skipping column {output_col}: deps is not a list "
                    f"(type: {type(deps).__name__})"
                )
                continue

            for dep in deps:
                # Validate dep is a dict before accessing properties
                if not isinstance(dep, dict):
                    logger.debug(
                        f"Skipping column {output_col}: dep is not a dict "
                        f"(type: {type(dep).__name__})"
                    )
                    continue

                dep_asset_key = "::".join(dep.get("asset_key", {}).get("path", []))
                upstream_col = dep.get("column_name", "")

                # Skip dependencies with missing or empty asset keys
                if not dep_asset_key:
                    logger.debug(
                        f"Skipping column lineage dependency with missing asset_key "
                        f"for column {output_col}"
                    )
                    continue

                upstream_schema, upstream_table = self._map_asset_to_table(dep_asset_key)

                # Skip if upstream table is empty (invalid mapping)
                if not upstream_table:
                    logger.debug(
                        f"Skipping column lineage dependency with invalid asset_key "
                        f"{dep_asset_key} for column {output_col}"
                    )
                    continue

                edge = ColumnLineageEdge(
                    downstream_schema=downstream_schema,
                    downstream_table=downstream_table,
                    downstream_column=output_col,
                    upstream_schema=upstream_schema,
                    upstream_table=upstream_table,
                    upstream_column=upstream_col,
                    lineage_type="dagster_column",
                    provider="dagster",
                    confidence_score=1.0,
                    metadata={"source": "dagster_metadata"},
                )
                edges.append(edge)

        return edges

    def get_all_lineage(self) -> Dict[str, List[LineageEdge]]:
        """
        Extract lineage for all assets (bulk operation).

        Returns:
            Dictionary mapping table identifiers to lists of LineageEdge objects
        """
        if not self.is_available():
            return {}

        all_lineage = {}

        # Extract all assets based on data source
        if self._available_data_source == "metadata_db":
            all_lineage = self._get_all_lineage_from_metadata_db()
        elif self._available_data_source == "code":
            all_lineage = self._get_all_lineage_from_code()
        elif self._available_data_source == "graphql":
            all_lineage = self._get_all_lineage_from_graphql()

        return all_lineage

    def _get_all_lineage_from_metadata_db(self) -> Dict[str, List[LineageEdge]]:
        """Get all lineage from metadata database."""
        all_lineage: Dict[str, List[LineageEdge]] = {}
        if not self._metadata_db_engine:
            return all_lineage

        try:
            with self._metadata_db_engine.connect() as conn:
                # Query all materialization events from event_logs
                results = None
                for table_variant in ["public.event_logs", "event_logs"]:
                    try:
                        query = text(
                            f"""
                            SELECT e.event, e.asset_key
                            FROM {table_variant} e
                            WHERE e.dagster_event_type = 'ASSET_MATERIALIZATION'
                            ORDER BY e.id DESC
                            """
                        )
                        results = conn.execute(query).fetchall()
                        if results:
                            break
                    except Exception as e:
                        logger.debug(f"Error querying {table_variant}: {e}")
                        continue

                if not results:
                    return all_lineage

                for row in results:
                    event_json = row[0]
                    asset_key_str = row[1]

                    try:
                        event_data = json.loads(event_json)
                        dependencies = self._extract_dependencies_from_event(event_data)

                        if dependencies:
                            downstream_schema, downstream_table = self._map_asset_to_table(
                                asset_key_str
                            )
                            table_id = f"{downstream_schema}.{downstream_table}"

                            edges: List[LineageEdge] = []
                            for dep_asset_key in dependencies:
                                upstream_schema, upstream_table = self._map_asset_to_table(
                                    dep_asset_key
                                )

                                edge = LineageEdge(
                                    downstream_schema=downstream_schema,
                                    downstream_table=downstream_table,
                                    upstream_schema=upstream_schema,
                                    upstream_table=upstream_table,
                                    lineage_type="dagster_asset",
                                    provider="dagster",
                                    confidence_score=1.0,
                                    metadata={
                                        "asset_key": asset_key_str,
                                        "depends_on": dep_asset_key,
                                    },
                                )
                                edges.append(edge)

                            if edges:
                                all_lineage[table_id] = edges
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug(f"Error parsing event for asset {asset_key_str}: {e}")
                        continue

        except Exception as e:
            logger.debug(f"Error getting all Dagster lineage from metadata DB: {e}")

        return all_lineage

    def _get_all_lineage_from_code(self) -> Dict[str, List[LineageEdge]]:
        """Get all lineage from code scanning."""
        all_lineage = {}
        for location in self.code_locations:
            location_lineage = self._scan_code_location_for_all(location)
            all_lineage.update(location_lineage)

        return all_lineage

    def _scan_code_location_for_all(self, location: str) -> Dict[str, List[LineageEdge]]:
        """Scan code location and extract all asset lineage."""
        all_lineage: Dict[str, List[LineageEdge]] = {}
        path = Path(location)

        if not path.exists():
            return all_lineage

        python_files = list(path.rglob("*.py"))

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Call):
                                if (
                                    isinstance(decorator.func, ast.Name)
                                    and decorator.func.id == "asset"
                                ):
                                    asset_name = self._get_asset_name_from_node(node)
                                    deps = []
                                    for keyword in decorator.keywords:
                                        if keyword.arg == "deps":
                                            if isinstance(keyword.value, ast.List):
                                                deps = [
                                                    self._ast_to_asset_key(elem)
                                                    for elem in keyword.value.elts
                                                ]

                                    if deps:
                                        downstream_schema, downstream_table = (
                                            self._map_asset_to_table(asset_name)
                                        )
                                        table_id = f"{downstream_schema}.{downstream_table}"

                                        edges = []
                                        for dep_asset_key in deps:
                                            upstream_schema, upstream_table = (
                                                self._map_asset_to_table(dep_asset_key)
                                            )

                                            edge = LineageEdge(
                                                downstream_schema=downstream_schema,
                                                downstream_table=downstream_table,
                                                upstream_schema=upstream_schema,
                                                upstream_table=upstream_table,
                                                lineage_type="dagster_asset",
                                                provider="dagster",
                                                confidence_score=0.9,
                                                metadata={
                                                    "asset_key": asset_name,
                                                    "depends_on": dep_asset_key,
                                                    "source_file": str(py_file),
                                                },
                                            )
                                            edges.append(edge)

                                        if edges:
                                            all_lineage[table_id] = edges

            except Exception as e:
                logger.debug(f"Error scanning file {py_file}: {e}")

        return all_lineage

    def _get_all_lineage_from_graphql(self) -> Dict[str, List[LineageEdge]]:
        """Get all lineage from GraphQL API."""
        # Implementation would query all assets from GraphQL
        return {}

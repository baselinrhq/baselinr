"""
dbt lineage provider for Baselinr.

Extracts lineage from dbt manifest.json files.
"""

import logging
from typing import List, Optional

from .base import ColumnLineageEdge, LineageEdge, LineageProvider

# Optional dbt integration
try:
    from ..dbt import DBTManifestParser

    DBT_AVAILABLE = True
except ImportError:
    DBT_AVAILABLE = False

logger = logging.getLogger(__name__)


class DBTLineageProvider(LineageProvider):
    """Lineage provider that extracts dependencies from dbt manifest.json."""

    def __init__(self, manifest_path: Optional[str] = None, project_path: Optional[str] = None):
        """
        Initialize dbt lineage provider.

        Args:
            manifest_path: Path to dbt manifest.json file
            project_path: Path to dbt project root (used to auto-detect manifest)
        """
        self.manifest_path = manifest_path
        self.project_path = project_path
        self._parser: Optional[DBTManifestParser] = None

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "dbt"

    def is_available(self) -> bool:
        """
        Check if dbt provider is available.

        Returns:
            True if dbt is available and manifest can be loaded
        """
        if not DBT_AVAILABLE:
            return False

        try:
            # Try to load manifest
            parser = DBTManifestParser(
                manifest_path=self.manifest_path, project_path=self.project_path
            )
            parser.get_manifest()
            self._parser = parser
            return True
        except (FileNotFoundError, ValueError) as e:
            logger.debug(f"dbt provider not available: {e}")
            return False
        except Exception as e:
            logger.debug(f"dbt provider error: {e}")
            return False

    def extract_lineage(self, table_name: str, schema: Optional[str] = None) -> List[LineageEdge]:
        """
        Extract lineage for a specific table from dbt manifest.

        Args:
            table_name: Name of the table
            schema: Optional schema name

        Returns:
            List of LineageEdge objects representing upstream dependencies
        """
        if not self.is_available():
            return []

        if self._parser is None:
            self._parser = DBTManifestParser(
                manifest_path=self.manifest_path, project_path=self.project_path
            )
            try:
                self._parser.get_manifest()
            except Exception as e:
                logger.warning(f"Failed to load dbt manifest: {e}")
                return []

        try:
            # Get dependencies for this model
            # First, try to find the model by table name
            manifest = self._parser.get_manifest()
            nodes = manifest.get("nodes", {})

            # Find model that matches this table
            matching_model = None
            for node_id, node in nodes.items():
                if node.get("resource_type") != "model":
                    continue

                node_schema, node_table = self._parser.model_to_table(node)
                if node_table == table_name and (schema is None or node_schema == schema):
                    matching_model = node
                    break

            if not matching_model:
                # Table not found in dbt models
                return []

            # Get upstream dependencies
            upstream_tables = self._parser.get_model_dependencies(matching_model.get("name"))

            # Convert to LineageEdge objects
            downstream_schema = matching_model.get("schema", "")
            downstream_table = matching_model.get("alias") or matching_model.get("name", "")

            edges = []
            for upstream_schema, upstream_table in upstream_tables:
                # Determine lineage type based on how dependency is referenced
                # For now, default to 'dbt_ref' (could be enhanced to detect 'dbt_source')
                lineage_type = "dbt_ref"

                edge = LineageEdge(
                    downstream_schema=downstream_schema,
                    downstream_table=downstream_table,
                    upstream_schema=upstream_schema,
                    upstream_table=upstream_table,
                    lineage_type=lineage_type,
                    provider="dbt",
                    confidence_score=1.0,
                    metadata={"model_name": matching_model.get("name")},
                )
                edges.append(edge)

            return edges

        except Exception as e:
            logger.warning(f"Error extracting dbt lineage for {schema}.{table_name}: {e}")
            return []

    def get_all_lineage(self) -> dict:
        """
        Extract lineage for all models in manifest (bulk operation).

        Returns:
            Dictionary mapping table identifiers to lists of LineageEdge objects
        """
        if not self.is_available():
            return {}

        if self._parser is None:
            self._parser = DBTManifestParser(
                manifest_path=self.manifest_path, project_path=self.project_path
            )
            try:
                self._parser.get_manifest()
            except Exception as e:
                logger.warning(f"Failed to load dbt manifest: {e}")
                return {}

        try:
            lineage_dict = self._parser.extract_lineage()
            result = {}

            for downstream_key, upstream_tables in lineage_dict.items():
                # Parse downstream key (schema.table)
                parts = downstream_key.split(".", 1)
                if len(parts) == 2:
                    downstream_schema, downstream_table = parts
                else:
                    downstream_schema = ""
                    downstream_table = parts[0]

                edges = []
                for upstream_schema, upstream_table in upstream_tables:
                    edge = LineageEdge(
                        downstream_schema=downstream_schema,
                        downstream_table=downstream_table,
                        upstream_schema=upstream_schema,
                        upstream_table=upstream_table,
                        lineage_type="dbt_ref",
                        provider="dbt",
                        confidence_score=1.0,
                        metadata={},
                    )
                    edges.append(edge)

                result[downstream_key] = edges

            return result

        except Exception as e:
            logger.warning(f"Error extracting all dbt lineage: {e}")
            return {}

    def extract_column_lineage(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ColumnLineageEdge]:
        """
        Extract column-level lineage for a specific table from dbt manifest.

        dbt stores column-level lineage in manifest.nodes[].columns metadata,
        which can reference upstream columns via depends_on.columns.

        Args:
            table_name: Name of the table
            schema: Optional schema name

        Returns:
            List of ColumnLineageEdge objects representing column dependencies
        """
        if not self.is_available():
            return []

        if self._parser is None:
            self._parser = DBTManifestParser(
                manifest_path=self.manifest_path, project_path=self.project_path
            )
            try:
                self._parser.get_manifest()
            except Exception as e:
                logger.warning(f"Failed to load dbt manifest: {e}")
                return []

        try:
            manifest = self._parser.get_manifest()
            nodes = manifest.get("nodes", {})

            # Find model that matches this table
            matching_model = None
            available_models = []
            for node_id, node in nodes.items():
                if node.get("resource_type") != "model":
                    continue

                node_schema, node_table = self._parser.model_to_table(node)
                available_models.append(f"{node_schema}.{node_table}")
                if node_table == table_name and (schema is None or node_schema == schema):
                    matching_model = node
                    break

            if not matching_model:
                # Table not found in dbt models
                logger.info(
                    f"Table {schema}.{table_name} not found in dbt manifest models. "
                    f"Available models: {', '.join(available_models[:10])}"
                )
                return []

            logger.info(
                f"Found dbt model for {schema}.{table_name}: "
                f"{matching_model.get('name', 'unknown')}"
            )

            # Extract column-level lineage
            downstream_schema = matching_model.get("schema", "")
            downstream_table = matching_model.get("alias") or matching_model.get("name", "")

            column_edges: List[ColumnLineageEdge] = []

            # Get columns metadata for this model
            columns = matching_model.get("columns", {})
            depends_on = matching_model.get("depends_on", {})
            depends_on_nodes = depends_on.get("nodes", [])

            # Build mapping of upstream node IDs to their table info
            upstream_node_map = {}
            for upstream_node_id in depends_on_nodes:
                upstream_node = nodes.get(upstream_node_id)
                if upstream_node:
                    upstream_schema, upstream_table = self._parser.model_to_table(upstream_node)
                    upstream_node_map[upstream_node_id] = (upstream_schema, upstream_table)

            logger.info(f"Processing {len(columns)} columns for dbt model {schema}.{table_name}")

            # Process each column in the downstream model
            for column_name, column_info in columns.items():
                # Check if column has dependencies
                column_depends_on = column_info.get("depends_on", {})
                column_nodes = column_depends_on.get("nodes", [])

                # For each upstream node this column depends on
                for upstream_node_id in column_nodes:
                    if upstream_node_id not in upstream_node_map:
                        continue

                    upstream_schema, upstream_table = upstream_node_map[upstream_node_id]

                    # Try to find the specific upstream column
                    # dbt may store this in column_info.meta or in the upstream node's columns
                    upstream_column = None
                    upstream_node = nodes.get(upstream_node_id)
                    if upstream_node:
                        # Check if there's a direct column reference
                        # This is a simplified approach - dbt's column lineage can be complex
                        # For now, we'll create edges for all columns in upstream table
                        # that might be referenced (this is a limitation we can improve later)
                        # If we can't determine specific column, we'll skip for now
                        # In a more complete implementation, we'd parse the SQL to find
                        # which specific columns are referenced
                        continue

                    # If we have a specific upstream column, create edge
                    if upstream_column:
                        edge = ColumnLineageEdge(
                            downstream_schema=downstream_schema,
                            downstream_table=downstream_table,
                            downstream_column=column_name,
                            upstream_schema=upstream_schema,
                            upstream_table=upstream_table,
                            upstream_column=upstream_column,
                            lineage_type="dbt_column_ref",
                            provider="dbt",
                            confidence_score=1.0,
                            metadata={
                                "model_name": matching_model.get("name"),
                                "column_description": column_info.get("description"),
                            },
                        )
                        column_edges.append(edge)

            # Alternative approach: Parse SQL to extract column mappings
            # This is more reliable for column-level lineage
            compiled_code = matching_model.get("compiled_code") or matching_model.get("raw_code")
            if compiled_code:
                logger.info(
                    f"Found SQL code for {schema}.{table_name}, "
                    f"parsing for column lineage (length: {len(compiled_code)} chars)"
                )
                # Use SQL parser to extract column-level dependencies from SQL
                # Import here to avoid circular dependency
                from .sql_provider import SQLLineageProvider

                # Create a temporary SQL provider instance (we need the engine for view definitions,
                # but for dbt we already have the SQL, so we can pass None)
                sql_provider = SQLLineageProvider(engine=None)
                sql_edges = sql_provider.extract_column_lineage_from_sql(
                    compiled_code,
                    (downstream_schema, downstream_table),
                    output_database=None,
                    default_database=None,
                    default_schema=downstream_schema,
                )
                logger.info(
                    f"SQL parser extracted {len(sql_edges)} column lineage edges "
                    f"from dbt SQL for {schema}.{table_name}"
                )
                column_edges.extend(sql_edges)
            else:
                logger.info(
                    f"No compiled_code or raw_code found for dbt model {schema}.{table_name}"
                )

            logger.info(
                f"dbt provider extracted {len(column_edges)} total column lineage edges "
                f"for {schema}.{table_name}"
            )
            return column_edges

        except Exception as e:
            logger.warning(f"Error extracting dbt column lineage for {schema}.{table_name}: {e}")
            return []

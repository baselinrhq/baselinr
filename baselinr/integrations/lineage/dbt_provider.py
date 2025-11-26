"""
dbt lineage provider for Baselinr.

Extracts lineage from dbt manifest.json files.
"""

import logging
from typing import List, Optional

from .base import LineageEdge, LineageProvider

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

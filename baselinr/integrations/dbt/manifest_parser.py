"""
dbt manifest parser for Baselinr.

Parses dbt manifest.json files and resolves model references to database tables.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DBTManifestParser:
    """Parser for dbt manifest.json files."""

    def __init__(self, manifest_path: Optional[str] = None, project_path: Optional[str] = None):
        """
        Initialize dbt manifest parser.

        Args:
            manifest_path: Path to dbt manifest.json file
            project_path: Path to dbt project root (used to auto-detect manifest)
        """
        self.project_path = Path(project_path) if project_path else None
        self.manifest_path = Path(manifest_path) if manifest_path else None
        self._manifest: Optional[Dict[str, Any]] = None
        self._manifest_cache: Dict[str, Dict[str, Any]] = {}  # Cache by path

    def load_manifest(self, manifest_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load and parse dbt manifest.json.

        Args:
            manifest_path: Optional path to manifest (uses instance path if not provided)

        Returns:
            Parsed manifest dictionary

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            ValueError: If manifest is invalid JSON
        """
        # Determine manifest path
        if manifest_path:
            path = Path(manifest_path)
        elif self.manifest_path:
            path = self.manifest_path
        elif self.project_path:
            # Auto-detect manifest in target/ directory
            path = self.project_path / "target" / "manifest.json"
        else:
            raise ValueError(
                "No manifest path provided. Set manifest_path or project_path in constructor."
            )

        path_str = str(path.absolute())

        # Check cache
        if path_str in self._manifest_cache:
            logger.debug(f"Using cached manifest from {path_str}")
            self._manifest = self._manifest_cache[path_str]
            return self._manifest

        # Load manifest
        if not path.exists():
            raise FileNotFoundError(f"dbt manifest not found: {path}")

        try:
            with open(path, "r") as f:
                self._manifest = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in manifest file: {e}")

        # Cache it
        self._manifest_cache[path_str] = self._manifest
        logger.info(
            f"Loaded dbt manifest from {path_str} with {len(self._manifest.get('nodes', {}))} nodes"
        )

        return self._manifest

    def get_manifest(self) -> Dict[str, Any]:
        """
        Get loaded manifest (loads if not already loaded).

        Returns:
            Manifest dictionary
        """
        if self._manifest is None:
            self.load_manifest()
        # After load_manifest(), _manifest is guaranteed to be set
        assert self._manifest is not None, "Manifest should be loaded after load_manifest()"
        return self._manifest

    def resolve_ref(
        self, model_name: str, package: Optional[str] = None
    ) -> Optional[Tuple[str, str]]:
        """
        Resolve a dbt ref() to actual database schema and table name.

        Args:
            model_name: dbt model name
            package: Optional package name (for cross-package refs)

        Returns:
            Tuple of (schema, table) or None if not found
        """
        manifest = self.get_manifest()
        nodes = manifest.get("nodes", {})

        # Search for model
        # dbt node IDs are like: model.project_name.model_name
        for node_id, node in nodes.items():
            if node.get("resource_type") != "model":
                continue

            node_name = node.get("name", "")
            node_package = node.get("package_name")

            # Check if this is the model we're looking for
            if node_name == model_name:
                # If package specified, must match
                if package and node_package != package:
                    continue
                # If no package specified, prefer current project but accept any
                # Found the model
                schema = node.get("schema", "")
                alias = node.get("alias") or node.get("name", "")
                return (schema, alias)

        return None

    def get_models_by_tag(self, tag: str) -> List[Dict]:
        """
        Get all models with a specific tag.

        Args:
            tag: Tag name to filter by

        Returns:
            List of model node dictionaries
        """
        manifest = self.get_manifest()
        nodes = manifest.get("nodes", {})
        models = []

        for node_id, node in nodes.items():
            if node.get("resource_type") == "model":
                tags = node.get("tags", [])
                if isinstance(tags, list) and tag in tags:
                    models.append(node)

        return models

    def get_all_models(self) -> List[Dict]:
        """
        Get all models from manifest.

        Returns:
            List of model node dictionaries
        """
        manifest = self.get_manifest()
        nodes = manifest.get("nodes", {})
        return [node for node in nodes.values() if node.get("resource_type") == "model"]

    def get_model_by_name(
        self, model_name: str, package: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific model by name.

        Args:
            model_name: Model name
            package: Optional package name

        Returns:
            Model node dictionary or None
        """
        manifest = self.get_manifest()
        nodes = manifest.get("nodes", {})

        for node_id, node in nodes.items():
            if (
                node.get("resource_type") == "model"
                and node.get("name") == model_name
                and (not package or node.get("package_name") == package)
            ):
                # Type cast since we know node is a Dict from JSON
                # json.load returns Dict[str, Any], so this is safe
                return node  # type: ignore[return-value,no-any-return]

        return None

    def model_to_table(self, model: Dict) -> Tuple[str, str]:
        """
        Convert a model node to (schema, table) tuple.

        Args:
            model: Model node dictionary

        Returns:
            Tuple of (schema, table)
        """
        schema = model.get("schema", "")
        alias = model.get("alias") or model.get("name", "")
        return (schema, alias)

    def extract_lineage(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Extract table-to-table lineage from manifest.

        Returns:
            Dictionary mapping downstream table (schema.table) to list of upstream tables
        """
        manifest = self.get_manifest()
        nodes = manifest.get("nodes", {})
        lineage: Dict[str, List[Tuple[str, str]]] = {}

        for node_id, node in nodes.items():
            if node.get("resource_type") != "model":
                continue

            downstream_schema, downstream_table = self.model_to_table(node)
            downstream_key = f"{downstream_schema}.{downstream_table}"

            # Get dependencies
            depends_on = node.get("depends_on", {})
            depends_on_nodes = depends_on.get("nodes", [])

            upstream_tables = []
            for dep_id in depends_on_nodes:
                dep_node = nodes.get(dep_id)
                if dep_node and dep_node.get("resource_type") == "model":
                    dep_schema, dep_table = self.model_to_table(dep_node)
                    upstream_tables.append((dep_schema, dep_table))

            if upstream_tables:
                lineage[downstream_key] = upstream_tables

        return lineage

    def get_model_dependencies(
        self, model_name: str, package: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Get upstream dependencies for a specific model.

        Args:
            model_name: Model name
            package: Optional package name

        Returns:
            List of (schema, table) tuples for upstream dependencies
        """
        model = self.get_model_by_name(model_name, package)
        if not model:
            return []

        manifest = self.get_manifest()
        nodes = manifest.get("nodes", {})
        depends_on = model.get("depends_on", {})
        depends_on_nodes = depends_on.get("nodes", [])

        upstream_tables = []
        for dep_id in depends_on_nodes:
            dep_node = nodes.get(dep_id)
            if dep_node and dep_node.get("resource_type") == "model":
                dep_schema, dep_table = self.model_to_table(dep_node)
                upstream_tables.append((dep_schema, dep_table))

        return upstream_tables

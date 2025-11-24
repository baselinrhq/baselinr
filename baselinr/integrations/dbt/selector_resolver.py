"""
dbt selector resolver for Baselinr.

Resolves dbt selector expressions to lists of models.
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class DBTSelectorResolver:
    """Resolves dbt selector expressions to model lists."""

    def __init__(self, manifest_parser):
        """
        Initialize selector resolver.

        Args:
            manifest_parser: DBTManifestParser instance
        """
        self.manifest_parser = manifest_parser

    def resolve_selector(self, selector: str) -> List[Dict]:
        """
        Resolve a dbt selector expression to a list of models.

        Supports dbt selector syntax:
        - tag:tag_name - Models with tag
        - config.materialized:table - Models with specific config
        - path:models/staging - Models in path
        - package:package_name - Models in package
        - name:model_name - Specific model name
        - Multiple selectors can be combined with + (union) or , (intersection)

        Args:
            selector: dbt selector expression

        Returns:
            List of model node dictionaries
        """
        manifest = self.manifest_parser.get_manifest()
        nodes = manifest.get("nodes", {})
        all_models = [node for node in nodes.values() if node.get("resource_type") == "model"]

        # Parse selector expression
        # For now, support simple selectors. Full dbt selector syntax is complex
        # and would require implementing dbt's selector logic, which is extensive.
        # We'll support the most common patterns.

        # Split by + (union) or , (intersection)
        if "+" in selector:
            # Union: combine results
            parts = [p.strip() for p in selector.split("+")]
            results: set[str] = set()
            for part in parts:
                models = self._resolve_simple_selector(part, all_models)
                results.update(m.get("unique_id", "") for m in models)
            # Convert back to list
            model_map = {m.get("unique_id", ""): m for m in all_models}
            return [model_map[uid] for uid in results if uid in model_map]
        elif "," in selector:
            # Intersection: models matching all selectors
            parts = [p.strip() for p in selector.split(",")]
            if not parts:
                return []
            # Start with first selector
            results = set(
                m.get("unique_id", "") for m in self._resolve_simple_selector(parts[0], all_models)
            )
            # Intersect with remaining selectors
            for part in parts[1:]:
                models = self._resolve_simple_selector(part, all_models)
                model_ids = {m.get("unique_id", "") for m in models}
                results = results.intersection(model_ids)
            # Convert back to list
            model_map = {m.get("unique_id", ""): m for m in all_models}
            return [model_map[uid] for uid in results if uid in model_map]
        else:
            # Simple selector
            return self._resolve_simple_selector(selector, all_models)

    def _resolve_simple_selector(self, selector: str, all_models: List[Dict]) -> List[Dict]:
        """
        Resolve a simple selector expression (no operators).

        Args:
            selector: Simple selector expression
            all_models: List of all models

        Returns:
            List of matching models
        """
        selector = selector.strip()

        # tag:tag_name
        if selector.startswith("tag:"):
            tag = selector[4:].strip()
            return [m for m in all_models if tag in m.get("tags", [])]

        # config.materialized:value
        if selector.startswith("config.materialized:"):
            materialized = selector.split(":", 1)[1].strip()
            return [
                m for m in all_models if m.get("config", {}).get("materialized") == materialized
            ]

        # config.materialized:value (alternative syntax)
        if "materialized:" in selector:
            materialized = selector.split(":", 1)[1].strip()
            return [
                m for m in all_models if m.get("config", {}).get("materialized") == materialized
            ]

        # path:path_pattern
        if selector.startswith("path:"):
            path_pattern = selector[5:].strip()
            # Simple prefix matching for now
            return [
                m for m in all_models if m.get("original_file_path", "").startswith(path_pattern)
            ]

        # package:package_name
        if selector.startswith("package:"):
            package = selector[8:].strip()
            return [m for m in all_models if m.get("package_name") == package]

        # name:model_name
        if selector.startswith("name:"):
            name = selector[5:].strip()
            return [m for m in all_models if m.get("name") == name]

        # Just a model name (no prefix)
        # Check if it matches a model name
        matching = [m for m in all_models if m.get("name") == selector]
        if matching:
            return matching

        # If no match, return empty
        logger.warning(f"Selector '{selector}' did not match any models")
        return []

    def parse_selector_expression(self, expr: str) -> Dict:
        """
        Parse a selector expression into its components.

        This is a helper method for debugging and validation.

        Args:
            expr: Selector expression

        Returns:
            Dictionary with parsed components
        """
        result = {
            "original": expr,
            "type": "simple",
            "components": [],
        }

        if "+" in expr:
            result["type"] = "union"
            result["components"] = [p.strip() for p in expr.split("+")]
        elif "," in expr:
            result["type"] = "intersection"
            result["components"] = [p.strip() for p in expr.split(",")]
        else:
            result["components"] = [expr.strip()]

        return result

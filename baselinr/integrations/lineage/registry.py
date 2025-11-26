"""
Lineage provider registry for Baselinr.

Manages multiple lineage providers and coordinates lineage extraction.
"""

import logging
from typing import List, Optional

from .base import LineageEdge, LineageProvider

logger = logging.getLogger(__name__)


class LineageProviderRegistry:
    """Registry for managing lineage providers."""

    def __init__(self, config=None, source_engine=None):
        """
        Initialize registry.

        Args:
            config: Optional BaselinrConfig to pass to providers
            source_engine: Optional SQLAlchemy engine for source database (for SQL provider)
        """
        self.config = config
        self.source_engine = source_engine
        self._providers: List[LineageProvider] = []
        self._auto_register()

    def _auto_register(self):
        """Auto-register built-in providers."""
        # Register SQL provider (always available)
        try:
            from .sql_provider import SQLLineageProvider

            sql_provider = SQLLineageProvider(engine=self.source_engine)
            self.register_provider(sql_provider)
        except Exception as e:
            logger.debug(f"Could not register SQL provider: {e}")

        # Register dbt provider (optional)
        try:
            from .dbt_provider import DBTLineageProvider

            # Get dbt config if available
            manifest_path = None
            project_path = None
            if self.config and self.config.lineage and self.config.lineage.dbt:
                dbt_config = self.config.lineage.dbt
                manifest_path = (
                    dbt_config.get("manifest_path") if isinstance(dbt_config, dict) else None
                )
                # Could also get project_path from dbt config if needed

            # DBT provider will check availability when needed
            dbt_provider = DBTLineageProvider(
                manifest_path=manifest_path, project_path=project_path
            )
            self.register_provider(dbt_provider)
        except Exception as e:
            logger.debug(f"Could not register dbt provider: {e}")

    def register_provider(self, provider: LineageProvider):
        """
        Register a lineage provider.

        Args:
            provider: LineageProvider instance
        """
        if provider not in self._providers:
            self._providers.append(provider)
            logger.debug(f"Registered lineage provider: {provider.get_provider_name()}")

    def get_available_providers(self) -> List[LineageProvider]:
        """
        Get list of available providers.

        Returns:
            List of providers where is_available() returns True
        """
        return [p for p in self._providers if p.is_available()]

    def get_provider(self, name: str) -> Optional[LineageProvider]:
        """
        Get a specific provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None if not found
        """
        for provider in self._providers:
            if provider.get_provider_name() == name:
                return provider
        return None

    def extract_lineage_for_table(
        self,
        table_name: str,
        schema: Optional[str] = None,
        enabled_providers: Optional[List[str]] = None,
    ) -> List[LineageEdge]:
        """
        Extract lineage for a table using all enabled/available providers.

        Args:
            table_name: Name of the table
            schema: Optional schema name
            enabled_providers: Optional list of provider names to use.
                             If None, uses all available providers.

        Returns:
            List of LineageEdge objects from all providers
        """
        if enabled_providers:
            # Use only specified providers
            providers_to_use = [
                p
                for p in self._providers
                if p.get_provider_name() in enabled_providers and p.is_available()
            ]
        else:
            # Use all available providers
            providers_to_use = self.get_available_providers()

        if not providers_to_use:
            logger.debug(f"No lineage providers available for {schema}.{table_name}")
            return []

        all_edges = []
        for provider in providers_to_use:
            try:
                edges = provider.extract_lineage(table_name, schema)
                all_edges.extend(edges)
                logger.debug(
                    f"Provider {provider.get_provider_name()} extracted "
                    f"{len(edges)} lineage edges for {schema}.{table_name}"
                )
            except Exception as e:
                logger.warning(
                    f"Provider {provider.get_provider_name()} failed to extract "
                    f"lineage for {schema}.{table_name}: {e}"
                )
                # Continue with other providers
                continue

        # Deduplicate edges (same downstream/upstream/provider combination)
        seen = set()
        unique_edges = []
        for edge in all_edges:
            key = (
                edge.downstream_schema,
                edge.downstream_table,
                edge.upstream_schema,
                edge.upstream_table,
                edge.provider,
            )
            if key not in seen:
                seen.add(key)
                unique_edges.append(edge)

        return unique_edges

"""
Base classes for lineage providers.

Defines the abstract interface that all lineage providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LineageEdge:
    """Represents a single lineage edge (dependency relationship)."""

    downstream_schema: str
    downstream_table: str
    upstream_schema: str
    upstream_table: str
    downstream_database: Optional[str] = None
    upstream_database: Optional[str] = None
    lineage_type: str = "unknown"  # e.g., 'dbt_ref', 'dbt_source', 'sql_parsed', 'dagster_asset'
    provider: str = "unknown"  # Provider name (e.g., 'dbt', 'sql_parser', 'dagster')
    confidence_score: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "downstream_schema": self.downstream_schema,
            "downstream_table": self.downstream_table,
            "upstream_schema": self.upstream_schema,
            "upstream_table": self.upstream_table,
            "downstream_database": self.downstream_database,
            "upstream_database": self.upstream_database,
            "lineage_type": self.lineage_type,
            "provider": self.provider,
            "confidence_score": self.confidence_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineageEdge":
        """Create from dictionary."""
        return cls(
            downstream_schema=data["downstream_schema"],
            downstream_table=data["downstream_table"],
            upstream_schema=data["upstream_schema"],
            upstream_table=data["upstream_table"],
            downstream_database=data.get("downstream_database"),
            upstream_database=data.get("upstream_database"),
            lineage_type=data.get("lineage_type", "unknown"),
            provider=data.get("provider", "unknown"),
            confidence_score=data.get("confidence_score", 1.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ColumnLineageEdge:
    """Represents a column-level lineage edge (column dependency relationship)."""

    downstream_schema: str
    downstream_table: str
    downstream_column: str
    upstream_schema: str
    upstream_table: str
    upstream_column: str
    downstream_database: Optional[str] = None
    upstream_database: Optional[str] = None
    lineage_type: str = "unknown"  # e.g., 'dbt_ref', 'dbt_source', 'sql_parsed', 'query_history'
    provider: str = "unknown"  # Provider name (e.g., 'dbt', 'sql_parser', 'query_history')
    confidence_score: float = 1.0  # 0.0 to 1.0
    transformation_expression: Optional[str] = None  # SQL expression if available
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "downstream_schema": self.downstream_schema,
            "downstream_table": self.downstream_table,
            "downstream_column": self.downstream_column,
            "upstream_schema": self.upstream_schema,
            "upstream_table": self.upstream_table,
            "upstream_column": self.upstream_column,
            "downstream_database": self.downstream_database,
            "upstream_database": self.upstream_database,
            "lineage_type": self.lineage_type,
            "provider": self.provider,
            "confidence_score": self.confidence_score,
            "transformation_expression": self.transformation_expression,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ColumnLineageEdge":
        """Create from dictionary."""
        return cls(
            downstream_schema=data["downstream_schema"],
            downstream_table=data["downstream_table"],
            downstream_column=data["downstream_column"],
            upstream_schema=data["upstream_schema"],
            upstream_table=data["upstream_table"],
            upstream_column=data["upstream_column"],
            downstream_database=data.get("downstream_database"),
            upstream_database=data.get("upstream_database"),
            lineage_type=data.get("lineage_type", "unknown"),
            provider=data.get("provider", "unknown"),
            confidence_score=data.get("confidence_score", 1.0),
            transformation_expression=data.get("transformation_expression"),
            metadata=data.get("metadata", {}),
        )


class LineageProvider(ABC):
    """
    Abstract base class for lineage providers.

    Each provider implements methods to extract lineage from a specific source
    (dbt, Dagster, SQL parsing, etc.). Providers are optional and should
    gracefully handle cases where they cannot be used.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.

        Returns:
            Provider name (e.g., 'dbt', 'sql_parser', 'dagster')
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this provider can be used.

        Returns:
            True if provider is available and can extract lineage, False otherwise
        """
        pass

    @abstractmethod
    def extract_lineage(self, table_name: str, schema: Optional[str] = None) -> List[LineageEdge]:
        """
        Extract lineage for a specific table.

        Args:
            table_name: Name of the table
            schema: Optional schema name

        Returns:
            List of LineageEdge objects representing upstream dependencies
        """
        pass

    def get_all_lineage(self) -> Dict[str, List[LineageEdge]]:
        """
        Extract lineage for all tables (bulk operation).

        This is optional - providers can implement this for efficiency
        when extracting lineage for multiple tables.

        Returns:
            Dictionary mapping table identifiers to lists of LineageEdge objects
        """
        # Default implementation returns empty dict
        # Providers can override for bulk extraction
        return {}

    def extract_column_lineage(
        self, table_name: str, schema: Optional[str] = None
    ) -> List["ColumnLineageEdge"]:
        """
        Extract column-level lineage for a specific table.

        Default implementation returns empty list.
        Providers can override to provide column-level lineage.

        Args:
            table_name: Name of the table
            schema: Optional schema name

        Returns:
            List of ColumnLineageEdge objects representing column dependencies
        """
        # Default implementation returns empty list
        # Providers can override to provide column-level lineage
        return []

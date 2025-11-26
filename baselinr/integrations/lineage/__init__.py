"""
Lineage integration for Baselinr.

Provides a provider-based architecture for extracting data lineage from
multiple sources (dbt, Dagster, SQL parsing, etc.).
"""

from .base import LineageEdge, LineageProvider
from .registry import LineageProviderRegistry

# Optional providers - import only if available
try:
    from .dbt_provider import DBTLineageProvider
except (ImportError, ModuleNotFoundError):
    DBTLineageProvider = None  # type: ignore

try:
    from .sql_provider import SQLLineageProvider
except (ImportError, ModuleNotFoundError):
    SQLLineageProvider = None  # type: ignore

__all__ = [
    "LineageProvider",
    "LineageEdge",
    "LineageProviderRegistry",
    "DBTLineageProvider",
    "SQLLineageProvider",
]

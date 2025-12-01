"""
Smart table selection with usage-based intelligence.

Provides intelligent table recommendations based on database usage patterns,
query frequency, and metadata to reduce configuration overhead.
"""

from .config import SmartSelectionConfig
from .metadata_collector import MetadataCollector, TableMetadata
from .recommender import RecommendationEngine, TableRecommendation
from .scorer import TableScorer

__all__ = [
    "SmartSelectionConfig",
    "MetadataCollector",
    "TableMetadata",
    "TableScorer",
    "RecommendationEngine",
    "TableRecommendation",
]

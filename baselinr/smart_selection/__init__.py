"""
Smart table and column selection with usage-based intelligence.

Provides intelligent table and column-level recommendations based on
database usage patterns, query frequency, metadata, and naming patterns
to reduce configuration overhead.

Phase 1: Table-level selection based on usage patterns
Phase 2: Column-level check recommendations based on metadata and statistics
"""

from .config import (
    ColumnInferenceConfig,
    ColumnPatternConfig,
    ColumnSelectionConfig,
    SmartSelectionConfig,
)
from .metadata_collector import MetadataCollector, TableMetadata
from .recommender import (
    ColumnCheckRecommendation,
    ColumnRecommendationEngine,
    RecommendationEngine,
    RecommendationReport,
    TableRecommendation,
)
from .scorer import TableScorer

# Column analysis submodule exports
from .column_analysis import (
    CheckInferencer,
    ColumnMetadata,
    ColumnStatistics,
    InferredCheck,
    MetadataAnalyzer,
    PatternMatch,
    PatternMatcher,
    StatisticalAnalyzer,
)

# Scoring submodule exports
from .scoring import CheckPrioritizer, ConfidenceScorer

# Learning submodule exports
from .learning import LearnedPattern, PatternLearner, PatternStore

__all__ = [
    # Config
    "SmartSelectionConfig",
    "ColumnSelectionConfig",
    "ColumnInferenceConfig",
    "ColumnPatternConfig",
    # Table-level (Phase 1)
    "MetadataCollector",
    "TableMetadata",
    "TableScorer",
    "RecommendationEngine",
    "TableRecommendation",
    "RecommendationReport",
    # Column-level (Phase 2)
    "ColumnRecommendationEngine",
    "ColumnCheckRecommendation",
    # Column analysis
    "MetadataAnalyzer",
    "ColumnMetadata",
    "StatisticalAnalyzer",
    "ColumnStatistics",
    "PatternMatcher",
    "PatternMatch",
    "CheckInferencer",
    "InferredCheck",
    # Scoring
    "ConfidenceScorer",
    "CheckPrioritizer",
    # Learning
    "PatternLearner",
    "LearnedPattern",
    "PatternStore",
]

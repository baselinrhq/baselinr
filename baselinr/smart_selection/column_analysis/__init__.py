"""
Column analysis module for smart column selection.

Provides metadata analysis, statistical analysis, pattern matching,
and check type inference for intelligent column-level recommendations.
"""

from .check_inferencer import CheckInferencer, InferredCheck
from .metadata_analyzer import ColumnMetadata, MetadataAnalyzer
from .pattern_matcher import PatternMatch, PatternMatcher
from .statistical_analyzer import ColumnStatistics, StatisticalAnalyzer

__all__ = [
    "MetadataAnalyzer",
    "ColumnMetadata",
    "StatisticalAnalyzer",
    "ColumnStatistics",
    "PatternMatcher",
    "PatternMatch",
    "CheckInferencer",
    "InferredCheck",
]

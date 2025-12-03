"""
Learning module for smart column selection.

Provides pattern learning from existing configurations
and persistent storage for learned patterns.
"""

from .pattern_learner import LearnedPattern, PatternLearner
from .pattern_store import PatternStore

__all__ = [
    "PatternLearner",
    "LearnedPattern",
    "PatternStore",
]

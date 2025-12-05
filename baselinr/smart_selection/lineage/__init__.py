"""
Lineage-aware prioritization for smart selection.

This module provides lineage-based scoring and prioritization to enhance
smart selection capabilities by considering table dependencies and
downstream impact.

Phase 3: Lineage-aware prioritization
- Queries existing lineage data
- Builds dependency graph
- Calculates impact scores
- Adjusts recommendations based on lineage position
"""

from .adapter import LineageAdapter
from .graph import LineageGraph, LineageNode
from .impact_scorer import BlastRadius, ImpactScore, ImpactScorer
from .lineage_scorer import LineageAwareScorer

__all__ = [
    # Adapter
    "LineageAdapter",
    # Graph
    "LineageGraph",
    "LineageNode",
    # Scoring
    "ImpactScorer",
    "ImpactScore",
    "BlastRadius",
    "LineageAwareScorer",
]

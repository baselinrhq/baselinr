"""
Impact scoring algorithm for lineage-aware prioritization.

Calculates impact scores based on table position in the lineage DAG,
downstream dependencies, and criticality of downstream assets.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .adapter import LineageAdapter
from .graph import LineageGraph, LineageNode

logger = logging.getLogger(__name__)


@dataclass
class BlastRadius:
    """
    Represents the impact/blast radius of a data quality issue in a table.

    Attributes:
        immediate_downstream: Count of direct downstream dependencies
        total_affected: Count of all transitive downstream tables
        critical_assets_affected: Count of critical downstream assets
        affected_exposures: List of affected exposures (dashboards, reports)
        affected_tables: List of all affected table identifiers
        estimated_user_impact: Impact level (NONE, LOW, MEDIUM, HIGH, CRITICAL)
    """

    immediate_downstream: int = 0
    total_affected: int = 0
    critical_assets_affected: int = 0
    affected_exposures: List[str] = field(default_factory=list)
    affected_tables: List[str] = field(default_factory=list)
    estimated_user_impact: str = "NONE"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "immediate_downstream": self.immediate_downstream,
            "total_affected": self.total_affected,
            "critical_assets_affected": self.critical_assets_affected,
            "affected_exposures": self.affected_exposures,
            "affected_tables": self.affected_tables[:10],  # Limit for display
            "estimated_user_impact": self.estimated_user_impact,
        }


@dataclass
class ImpactScore:
    """
    Complete impact score for a table.

    Attributes:
        table: Table name
        schema: Schema name
        total_score: Combined impact score (0.0 - 1.0)
        downstream_score: Score based on downstream dependencies
        depth_score: Score based on position in lineage (closer to source = higher)
        criticality_score: Score based on downstream critical assets
        fanout_score: Score based on branching factor
        blast_radius: BlastRadius object with detailed impact info
        position: Position in lineage (root, intermediate, leaf)
        node_type: Type of node (source, staging, intermediate, mart)
        is_critical_path: Whether on a critical path
        reasoning: Human-readable explanation of the score
    """

    table: str
    schema: str = ""
    total_score: float = 0.0
    downstream_score: float = 0.0
    depth_score: float = 0.0
    criticality_score: float = 0.0
    fanout_score: float = 0.0
    blast_radius: BlastRadius = field(default_factory=BlastRadius)
    position: str = "unknown"
    node_type: str = "unknown"
    is_critical_path: bool = False
    reasoning: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "table": self.table,
            "schema": self.schema,
            "total_score": round(self.total_score, 4),
            "component_scores": {
                "downstream": round(self.downstream_score, 4),
                "depth": round(self.depth_score, 4),
                "criticality": round(self.criticality_score, 4),
                "fanout": round(self.fanout_score, 4),
            },
            "blast_radius": self.blast_radius.to_dict(),
            "position": self.position,
            "node_type": self.node_type,
            "is_critical_path": self.is_critical_path,
            "reasoning": self.reasoning,
        }


@dataclass
class ScoringWeights:
    """Weights for impact score components."""

    downstream_count: float = 0.4
    criticality: float = 0.3
    depth_position: float = 0.2
    fanout: float = 0.1

    def validate(self) -> None:
        """Validate that weights sum to approximately 1.0."""
        total = self.downstream_count + self.criticality + self.depth_position + self.fanout
        if not (0.95 <= total <= 1.05):
            raise ValueError(f"Weights should sum to 1.0, got {total:.3f}")


@dataclass
class BoostFactors:
    """Boost/penalty factors for different table types."""

    root_tables: float = 1.25
    critical_path: float = 1.20
    high_fanout: float = 1.15
    leaf_tables: float = 0.60
    orphaned_tables: float = 0.50


class ImpactScorer:
    """
    Calculates impact scores for tables based on lineage position.

    Uses a weighted combination of:
    - Downstream dependency count
    - Graph depth position
    - Criticality of downstream assets
    - Fanout factor

    Scores are normalized to 0.0 - 1.0 range.
    """

    def __init__(
        self,
        graph: LineageGraph,
        weights: Optional[ScoringWeights] = None,
        boosts: Optional[BoostFactors] = None,
    ):
        """
        Initialize impact scorer.

        Args:
            graph: LineageGraph to score
            weights: Optional custom scoring weights
            boosts: Optional custom boost factors
        """
        self.graph = graph
        self.weights = weights or ScoringWeights()
        self.boosts = boosts or BoostFactors()

        # Validate weights
        self.weights.validate()

        # Precompute graph-wide metrics for normalization
        self._max_downstream: float = 1.0
        self._max_fanout: float = 1.0
        self._exposure_node_types = {"exposure", "dashboard", "report", "notebook", "ml_model"}

        self._compute_normalization_factors()

    def _compute_normalization_factors(self) -> None:
        """Compute factors needed for score normalization."""
        for node in self.graph.nodes.values():
            if node.total_downstream > self._max_downstream:
                self._max_downstream = float(node.total_downstream)
            if node.fanout_factor > self._max_fanout:
                self._max_fanout = float(node.fanout_factor)

    def score_table(
        self,
        table: str,
        schema: Optional[str] = None,
    ) -> Optional[ImpactScore]:
        """
        Calculate impact score for a specific table.

        Args:
            table: Table name
            schema: Optional schema name

        Returns:
            ImpactScore or None if table not in graph
        """
        node = self.graph.get_node(table, schema)
        if not node:
            return None

        return self._score_node(node)

    def _score_node(self, node: LineageNode) -> ImpactScore:
        """Calculate impact score for a lineage node."""
        # Calculate component scores
        downstream_score = self._calculate_downstream_score(node)
        depth_score = self._calculate_depth_score(node)
        criticality_score = self._calculate_criticality_score(node)
        fanout_score = self._calculate_fanout_score(node)

        # Calculate weighted total
        total_score = (
            self.weights.downstream_count * downstream_score
            + self.weights.criticality * criticality_score
            + self.weights.depth_position * depth_score
            + self.weights.fanout * fanout_score
        )

        # Apply boost/penalty factors
        boost_factor = self._calculate_boost_factor(node)
        total_score = min(1.0, total_score * boost_factor)

        # Calculate blast radius
        blast_radius = self._calculate_blast_radius(node)

        # Determine position
        if node.is_root and not node.is_orphaned:
            position = "root"
        elif node.is_leaf:
            position = "leaf"
        elif node.is_orphaned:
            position = "orphaned"
        else:
            position = "intermediate"

        # Generate reasoning
        reasoning = self._generate_reasoning(
            node,
            downstream_score,
            depth_score,
            criticality_score,
            fanout_score,
            boost_factor,
            blast_radius,
        )

        return ImpactScore(
            table=node.table,
            schema=node.schema,
            total_score=total_score,
            downstream_score=downstream_score,
            depth_score=depth_score,
            criticality_score=criticality_score,
            fanout_score=fanout_score,
            blast_radius=blast_radius,
            position=position,
            node_type=node.node_type,
            is_critical_path=node.critical_path_member,
            reasoning=reasoning,
        )

    def _calculate_downstream_score(self, node: LineageNode) -> float:
        """
        Calculate score based on downstream dependency count.

        Uses logarithmic scaling to prevent extreme outliers.
        Score: log(1 + total_downstream) / log(1 + max_downstream_in_graph)
        """
        if node.total_downstream == 0:
            return 0.0

        log_count = math.log(1 + node.total_downstream)
        log_max = math.log(1 + self._max_downstream)

        return min(1.0, log_count / log_max) if log_max > 0 else 0.0

    def _calculate_depth_score(self, node: LineageNode) -> float:
        """
        Calculate score based on position in lineage.

        Earlier tables (closer to sources) get higher scores since
        upstream tables affect everything downstream.
        Score: (max_depth - node_depth) / max_depth
        """
        if self.graph.max_depth == 0:
            return 0.5  # Neutral score if no depth information

        # Invert depth so closer to source = higher score
        inverted_depth = self.graph.max_depth - node.depth
        return inverted_depth / self.graph.max_depth

    def _calculate_criticality_score(self, node: LineageNode) -> float:
        """
        Calculate score based on criticality of downstream assets.

        Higher score if downstream includes BI tools, dashboards, or reports.
        Score: critical_downstream_count / total_downstream_count
        """
        if node.total_downstream == 0:
            # No downstream - check if this node itself is an exposure
            if node.node_type in self._exposure_node_types:
                return 1.0
            return 0.0

        # Count critical downstream nodes
        critical_count: float = 0.0
        downstream_keys = self._get_all_downstream_keys(node)

        for key in downstream_keys:
            downstream_node = self.graph.nodes.get(key)
            if downstream_node:
                if downstream_node.node_type in self._exposure_node_types:
                    critical_count += 1.0
                # Also count marts as somewhat critical
                elif downstream_node.node_type == "mart":
                    critical_count += 0.5

        return min(1.0, critical_count / len(downstream_keys)) if downstream_keys else 0.0

    def _calculate_fanout_score(self, node: LineageNode) -> float:
        """
        Calculate score based on fanout factor.

        High fanout = single issue affects many independent pipelines.
        Score: unique_downstream_branches / max_branches_in_graph
        """
        if self._max_fanout == 0 or node.fanout_factor == 0:
            return 0.0

        return min(1.0, node.fanout_factor / self._max_fanout)

    def _calculate_boost_factor(self, node: LineageNode) -> float:
        """Calculate boost/penalty factor based on node characteristics."""
        boost = 1.0

        # Root tables (sources) - higher priority
        if node.is_root and not node.is_orphaned:
            boost = max(boost, self.boosts.root_tables)

        # Critical path tables - higher priority
        if node.critical_path_member:
            boost *= self.boosts.critical_path

        # High fanout tables - higher priority
        if node.fanout_factor > self._max_fanout * 0.5:
            boost *= self.boosts.high_fanout

        # Leaf tables (unused outputs) - lower priority
        if node.is_leaf and not node.is_root:
            boost = min(boost, self.boosts.leaf_tables)

        # Orphaned tables - lowest priority
        if node.is_orphaned:
            boost = min(boost, self.boosts.orphaned_tables)

        return boost

    def _calculate_blast_radius(self, node: LineageNode) -> BlastRadius:
        """Calculate the blast radius for a node."""
        downstream_keys = self._get_all_downstream_keys(node)
        exposures = []
        critical_count = 0
        total_affected = len(downstream_keys)

        for key in downstream_keys:
            downstream_node = self.graph.nodes.get(key)
            if downstream_node:
                if downstream_node.node_type in self._exposure_node_types:
                    exposures.append(key)
                    critical_count += 1
                elif downstream_node.node_type == "mart":
                    critical_count += 1

        # Estimate user impact
        if critical_count == 0 and total_affected == 0:
            impact = "NONE"
        elif critical_count == 0:
            impact = "LOW"
        elif critical_count <= 2:
            impact = "MEDIUM"
        elif critical_count <= 5:
            impact = "HIGH"
        else:
            impact = "CRITICAL"

        return BlastRadius(
            immediate_downstream=node.downstream_count,
            total_affected=total_affected,
            critical_assets_affected=critical_count,
            affected_exposures=exposures[:20],  # Limit for display
            affected_tables=list(downstream_keys)[:50],  # Limit for display
            estimated_user_impact=impact,
        )

    def _get_all_downstream_keys(self, node: LineageNode) -> List[str]:
        """Get all downstream node keys for a node."""
        visited: set = set()

        def collect(key: str):
            if key in visited or key not in self.graph.nodes:
                return
            visited.add(key)
            for downstream_key in self.graph.nodes[key].downstream:
                collect(downstream_key)

        for downstream_key in node.downstream:
            collect(downstream_key)

        return list(visited)

    def _generate_reasoning(
        self,
        node: LineageNode,
        downstream_score: float,
        depth_score: float,
        criticality_score: float,
        fanout_score: float,
        boost_factor: float,
        blast_radius: BlastRadius,
    ) -> List[str]:
        """Generate human-readable reasoning for the score."""
        reasons = []

        # Position-based reasoning
        if node.is_root and not node.is_orphaned:
            reasons.append("Root table - all downstream depends on this")
        elif node.is_orphaned:
            reasons.append("Orphaned table - no dependencies")
        elif node.is_leaf:
            reasons.append("Leaf table - no downstream dependencies")

        # Downstream impact
        if node.total_downstream > 0:
            reasons.append(f"Feeds {node.total_downstream} downstream tables")

        # Critical path
        if node.critical_path_member:
            reasons.append("On critical path to important assets")

        # Exposures
        if blast_radius.affected_exposures:
            num_exposures = len(blast_radius.affected_exposures)
            reasons.append(f"Affects {num_exposures} BI exposure(s)")

        # Blast radius
        if blast_radius.estimated_user_impact in ["HIGH", "CRITICAL"]:
            impact = blast_radius.estimated_user_impact
            reasons.append(f"{impact} blast radius - issues affect many downstream assets")

        # Boost factors applied
        if boost_factor > 1.0:
            if node.is_root:
                reasons.append("Score boosted due to root position")
            if node.critical_path_member:
                reasons.append("Score boosted due to critical path membership")
        elif boost_factor < 1.0:
            if node.is_orphaned:
                reasons.append("Score penalized - orphaned table")
            elif node.is_leaf:
                reasons.append("Score reduced - leaf table with no downstream impact")

        if not reasons:
            reasons.append("Standard intermediate table")

        return reasons

    def score_all_tables(self) -> Dict[str, ImpactScore]:
        """
        Calculate impact scores for all tables in the graph.

        Returns:
            Dictionary mapping table identifiers to ImpactScore objects
        """
        scores = {}
        for key, node in self.graph.nodes.items():
            scores[key] = self._score_node(node)
        return scores

    def get_top_impact_tables(self, limit: int = 10) -> List[ImpactScore]:
        """
        Get tables with highest impact scores.

        Args:
            limit: Maximum number of tables to return

        Returns:
            List of ImpactScore objects, sorted by score descending
        """
        all_scores = self.score_all_tables()
        sorted_scores = sorted(
            all_scores.values(),
            key=lambda s: s.total_score,
            reverse=True,
        )
        return sorted_scores[:limit]


def create_impact_scorer(
    adapter: LineageAdapter,
    weights: Optional[Dict[str, float]] = None,
    boosts: Optional[Dict[str, float]] = None,
) -> ImpactScorer:
    """
    Factory function to create an ImpactScorer from a LineageAdapter.

    Args:
        adapter: LineageAdapter for querying lineage data
        weights: Optional scoring weights dictionary
        boosts: Optional boost factors dictionary

    Returns:
        Configured ImpactScorer
    """
    # Build the graph
    graph = LineageGraph.build_from_adapter(adapter)

    # Create weights if provided
    scoring_weights = None
    if weights:
        scoring_weights = ScoringWeights(
            downstream_count=weights.get("downstream_count", 0.4),
            criticality=weights.get("criticality", 0.3),
            depth_position=weights.get("depth_position", 0.2),
            fanout=weights.get("fanout", 0.1),
        )

    # Create boosts if provided
    boost_factors = None
    if boosts:
        boost_factors = BoostFactors(
            root_tables=boosts.get("root_tables", 1.25),
            critical_path=boosts.get("critical_path", 1.20),
            high_fanout=boosts.get("high_fanout", 1.15),
            leaf_tables=boosts.get("leaf_tables", 0.60),
            orphaned_tables=boosts.get("orphaned_tables", 0.50),
        )

    return ImpactScorer(graph, scoring_weights, boost_factors)

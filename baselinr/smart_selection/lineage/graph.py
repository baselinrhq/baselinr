"""
Lineage graph construction and analysis.

Builds an in-memory directed acyclic graph (DAG) representing table
dependencies for impact analysis.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .adapter import LineageAdapter

logger = logging.getLogger(__name__)


@dataclass
class LineageNode:
    """
    Represents a node (table) in the lineage graph.

    Attributes:
        table: Table name
        schema: Schema name
        database: Database name
        node_type: Type of node (source, staging, intermediate, mart, exposure)
        depth: Distance from root sources (0 = source)
        upstream_count: Number of direct upstream dependencies
        downstream_count: Number of direct downstream dependencies
        total_upstream: All transitive upstream dependencies
        total_downstream: All transitive downstream dependencies
        upstream: List of upstream node identifiers
        downstream: List of downstream node identifiers
        metadata: Additional context from lineage
    """

    table: str
    schema: str = ""
    database: Optional[str] = None
    node_type: str = "unknown"
    depth: int = 0
    upstream_count: int = 0
    downstream_count: int = 0
    total_upstream: int = 0
    total_downstream: int = 0
    upstream: List[str] = field(default_factory=list)
    downstream: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Computed metrics (set during graph analysis)
    fanout_factor: float = 0.0
    is_root: bool = False
    is_leaf: bool = False
    is_orphaned: bool = False
    critical_path_member: bool = False

    @property
    def identifier(self) -> str:
        """Get unique identifier for this node."""
        return f"{self.schema}.{self.table}" if self.schema else self.table

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "table": self.table,
            "schema": self.schema,
            "database": self.database,
            "node_type": self.node_type,
            "depth": self.depth,
            "upstream_count": self.upstream_count,
            "downstream_count": self.downstream_count,
            "total_upstream": self.total_upstream,
            "total_downstream": self.total_downstream,
            "fanout_factor": self.fanout_factor,
            "is_root": self.is_root,
            "is_leaf": self.is_leaf,
            "is_orphaned": self.is_orphaned,
            "critical_path_member": self.critical_path_member,
            "metadata": self.metadata,
        }


class LineageGraph:
    """
    In-memory directed acyclic graph representing table dependencies.

    Provides methods for traversing the graph and computing metrics
    for impact analysis.
    """

    def __init__(self):
        """Initialize an empty lineage graph."""
        self.nodes: Dict[str, LineageNode] = {}
        self._roots: List[str] = []
        self._leaves: List[str] = []
        self._orphans: List[str] = []
        self._max_depth: int = 0
        self._critical_paths: List[List[str]] = []
        self._built: bool = False

    @property
    def roots(self) -> List[LineageNode]:
        """Get root nodes (sources with no upstream)."""
        return [self.nodes[key] for key in self._roots if key in self.nodes]

    @property
    def leaves(self) -> List[LineageNode]:
        """Get leaf nodes (outputs with no downstream)."""
        return [self.nodes[key] for key in self._leaves if key in self.nodes]

    @property
    def orphans(self) -> List[LineageNode]:
        """Get orphaned nodes (not connected to main graph)."""
        return [self.nodes[key] for key in self._orphans if key in self.nodes]

    @property
    def max_depth(self) -> int:
        """Get maximum depth of the graph."""
        return self._max_depth

    @property
    def critical_paths(self) -> List[List[str]]:
        """Get critical paths through the graph."""
        return self._critical_paths

    @classmethod
    def build_from_adapter(cls, adapter: LineageAdapter) -> "LineageGraph":
        """
        Build a lineage graph from a LineageAdapter.

        Args:
            adapter: LineageAdapter to query lineage data

        Returns:
            Constructed LineageGraph
        """
        graph = cls()

        # Get all edges
        edges = adapter.get_all_edges()

        if not edges:
            logger.warning("No lineage edges found - graph will be empty")
            graph._built = True
            return graph

        # Build nodes from edges
        for edge in edges:
            # Downstream node
            downstream_key = f"{edge['downstream_schema']}.{edge['downstream_table']}"
            if downstream_key not in graph.nodes:
                graph.nodes[downstream_key] = LineageNode(
                    table=edge["downstream_table"],
                    schema=edge["downstream_schema"],
                    database=edge.get("downstream_database"),
                    metadata=edge.get("metadata", {}),
                )

            # Upstream node
            upstream_key = f"{edge['upstream_schema']}.{edge['upstream_table']}"
            if upstream_key not in graph.nodes:
                graph.nodes[upstream_key] = LineageNode(
                    table=edge["upstream_table"],
                    schema=edge["upstream_schema"],
                    database=edge.get("upstream_database"),
                    metadata=edge.get("metadata", {}),
                )

            # Add edge relationships
            if upstream_key not in graph.nodes[downstream_key].upstream:
                graph.nodes[downstream_key].upstream.append(upstream_key)
            if downstream_key not in graph.nodes[upstream_key].downstream:
                graph.nodes[upstream_key].downstream.append(downstream_key)

        # Compute node metrics
        graph._compute_node_metrics()

        # Identify special nodes
        graph._identify_special_nodes()

        # Compute depths
        graph._compute_depths()

        # Infer node types
        graph._infer_node_types()

        # Find critical paths
        graph._find_critical_paths()

        # Detect cycles
        graph._detect_cycles()

        graph._built = True
        logger.info(
            f"Built lineage graph: {len(graph.nodes)} nodes, "
            f"{len(graph._roots)} roots, {len(graph._leaves)} leaves, "
            f"max depth: {graph._max_depth}"
        )

        return graph

    def _compute_node_metrics(self) -> None:
        """Compute metrics for each node."""
        for key, node in self.nodes.items():
            # Direct counts
            node.upstream_count = len(node.upstream)
            node.downstream_count = len(node.downstream)

            # Transitive counts
            node.total_upstream = len(self._get_all_upstream(key))
            node.total_downstream = len(self._get_all_downstream(key))

            # Fanout factor - how many unique branches this node feeds
            if node.downstream_count > 0:
                # Count unique leaf nodes reachable from each immediate downstream
                branches: Set[str] = set()
                for downstream_key in node.downstream:
                    downstream_leaves = self._get_leaf_descendants(downstream_key)
                    branches.update(downstream_leaves)
                node.fanout_factor = len(branches)
            else:
                node.fanout_factor = 0

    def _identify_special_nodes(self) -> None:
        """Identify root, leaf, and orphaned nodes."""
        self._roots = []
        self._leaves = []
        self._orphans = []

        for key, node in self.nodes.items():
            # Root: no upstream dependencies
            if node.upstream_count == 0:
                node.is_root = True
                self._roots.append(key)

            # Leaf: no downstream dependencies
            if node.downstream_count == 0:
                node.is_leaf = True
                self._leaves.append(key)

            # Orphaned: both root and leaf (isolated node)
            if node.is_root and node.is_leaf:
                node.is_orphaned = True
                self._orphans.append(key)

    def _compute_depths(self) -> None:
        """Compute depth for each node using BFS from roots."""
        # Initialize all depths to -1 (unknown)
        for node in self.nodes.values():
            node.depth = -1

        # BFS from each root
        from collections import deque

        for root_key in self._roots:
            if self.nodes[root_key].depth == -1:
                queue: deque = deque([(root_key, 0)])
                while queue:
                    current_key, current_depth = queue.popleft()
                    if current_key not in self.nodes:
                        continue

                    current_node = self.nodes[current_key]

                    # Only update if we found a shorter path (or first path)
                    if current_node.depth == -1 or current_depth < current_node.depth:
                        current_node.depth = current_depth
                        self._max_depth = max(self._max_depth, current_depth)

                        for downstream_key in current_node.downstream:
                            if downstream_key in self.nodes:
                                queue.append((downstream_key, current_depth + 1))

        # Handle nodes not reachable from roots (shouldn't happen in a DAG)
        for node in self.nodes.values():
            if node.depth == -1:
                node.depth = 0  # Default to 0 for unreachable nodes

    def _infer_node_types(self) -> None:
        """Infer node types based on position and naming conventions."""
        for node in self.nodes.values():
            # Check if metadata already has node_type
            if node.metadata.get("node_type"):
                node.node_type = node.metadata["node_type"]
                continue

            # Infer from position
            if node.is_root:
                node.node_type = "source"
            elif node.is_leaf:
                # Check for exposure-like names
                name_lower = node.table.lower()
                if any(
                    kw in name_lower for kw in ["report", "dashboard", "export", "output", "mart"]
                ):
                    node.node_type = "mart"
                else:
                    node.node_type = "mart"  # Default leaf type
            elif node.depth <= 1:
                node.node_type = "staging"
            elif node.depth <= self._max_depth // 2:
                node.node_type = "intermediate"
            else:
                node.node_type = "mart"

            # Override based on naming patterns
            name_lower = node.table.lower()
            schema_lower = node.schema.lower() if node.schema else ""

            if any(kw in schema_lower for kw in ["raw", "source", "ingest"]):
                node.node_type = "source"
            elif any(kw in schema_lower for kw in ["stg", "staging"]):
                node.node_type = "staging"
            elif any(kw in schema_lower for kw in ["int", "intermediate"]):
                node.node_type = "intermediate"
            elif any(kw in schema_lower for kw in ["mart", "analytics", "report"]):
                node.node_type = "mart"

            # Table name patterns
            if name_lower.startswith("stg_"):
                node.node_type = "staging"
            elif name_lower.startswith("int_"):
                node.node_type = "intermediate"
            elif name_lower.startswith("fct_") or name_lower.startswith("dim_"):
                node.node_type = "mart"

    def _find_critical_paths(self, num_paths: int = 10) -> None:
        """
        Find critical paths through the graph.

        Critical paths are paths from roots to leaves that pass through
        high-impact nodes.

        Args:
            num_paths: Maximum number of critical paths to find
        """
        self._critical_paths = []

        # Find all paths from roots to leaves
        all_paths: List[Tuple[List[str], float]] = []

        for root_key in self._roots:
            paths = self._find_paths_to_leaves(root_key)
            for path in paths:
                # Score path based on downstream impact of nodes
                score = sum(self.nodes[key].total_downstream for key in path if key in self.nodes)
                all_paths.append((path, score))

        # Sort by score (descending) and take top paths
        all_paths.sort(key=lambda x: x[1], reverse=True)

        for path, _ in all_paths[:num_paths]:
            self._critical_paths.append(path)
            # Mark nodes as critical path members
            for node_key in path:
                if node_key in self.nodes:
                    self.nodes[node_key].critical_path_member = True

    def _find_paths_to_leaves(self, start_key: str, max_paths: int = 100) -> List[List[str]]:
        """Find all paths from a node to leaf nodes."""
        if start_key not in self.nodes:
            return []

        paths: List[List[str]] = []

        def dfs(current_key: str, current_path: List[str]):
            if len(paths) >= max_paths:
                return

            if current_key not in self.nodes:
                return

            node = self.nodes[current_key]
            current_path = current_path + [current_key]

            if node.is_leaf:
                paths.append(current_path)
                return

            for downstream_key in node.downstream:
                if downstream_key not in current_path:  # Avoid cycles
                    dfs(downstream_key, current_path)

        dfs(start_key, [])
        return paths

    def _detect_cycles(self) -> List[List[str]]:
        """
        Detect cycles in the graph.

        Returns:
            List of cycles (should be empty for a proper DAG)
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(key: str, path: List[str]) -> None:
            visited.add(key)
            rec_stack.add(key)

            if key in self.nodes:
                for downstream_key in self.nodes[key].downstream:
                    if downstream_key not in visited:
                        dfs(downstream_key, path + [key])
                    elif downstream_key in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(downstream_key) if downstream_key in path else 0
                        cycle = path[cycle_start:] + [key, downstream_key]
                        cycles.append(cycle)
                        logger.warning(f"Cycle detected in lineage graph: {cycle}")

            rec_stack.remove(key)

        for key in self.nodes:
            if key not in visited:
                dfs(key, [])

        return cycles

    def _get_all_upstream(self, key: str, visited: Optional[Set[str]] = None) -> Set[str]:
        """Get all transitive upstream nodes."""
        if visited is None:
            visited = set()

        result: Set[str] = set()

        def traverse(current_key: str):
            if current_key not in self.nodes or current_key in visited:
                return
            visited.add(current_key)

            for upstream_key in self.nodes[current_key].upstream:
                if upstream_key not in visited:
                    result.add(upstream_key)
                    traverse(upstream_key)

        traverse(key)
        return result

    def _get_all_downstream(self, key: str, visited: Optional[Set[str]] = None) -> Set[str]:
        """Get all transitive downstream nodes."""
        if visited is None:
            visited = set()

        result: Set[str] = set()

        def traverse(current_key: str):
            if current_key not in self.nodes or current_key in visited:
                return
            visited.add(current_key)

            for downstream_key in self.nodes[current_key].downstream:
                if downstream_key not in visited:
                    result.add(downstream_key)
                    traverse(downstream_key)

        traverse(key)
        return result

    def _get_leaf_descendants(self, key: str, visited: Optional[Set[str]] = None) -> Set[str]:
        """Get all leaf nodes reachable from this node."""
        if visited is None:
            visited = set()

        if key not in self.nodes or key in visited:
            return set()

        visited.add(key)
        node = self.nodes[key]

        if node.is_leaf:
            return {key}

        leaves: Set[str] = set()
        for downstream_key in node.downstream:
            leaves.update(self._get_leaf_descendants(downstream_key, visited))

        return leaves

    def get_node(self, table: str, schema: Optional[str] = None) -> Optional[LineageNode]:
        """
        Get a node from the graph.

        Args:
            table: Table name
            schema: Optional schema name

        Returns:
            LineageNode or None if not found
        """
        key = f"{schema}.{table}" if schema else f".{table}"
        if key in self.nodes:
            return self.nodes[key]

        # Try without schema prefix
        for node_key, node in self.nodes.items():
            if node.table == table and (schema is None or node.schema == schema):
                return node

        return None

    def get_subgraph(
        self,
        table: str,
        schema: Optional[str] = None,
        upstream_depth: int = 2,
        downstream_depth: int = 2,
    ) -> "LineageGraph":
        """
        Get a subgraph centered on a specific table.

        Args:
            table: Table name
            schema: Optional schema name
            upstream_depth: How many levels of upstream to include
            downstream_depth: How many levels of downstream to include

        Returns:
            New LineageGraph containing just the subgraph
        """
        subgraph = LineageGraph()
        center_node = self.get_node(table, schema)

        if not center_node:
            return subgraph

        # Collect nodes to include
        nodes_to_include: Set[str] = {center_node.identifier}

        # Upstream nodes
        def collect_upstream(key: str, depth: int):
            if depth > upstream_depth or key not in self.nodes:
                return
            nodes_to_include.add(key)
            for upstream_key in self.nodes[key].upstream:
                collect_upstream(upstream_key, depth + 1)

        # Downstream nodes
        def collect_downstream(key: str, depth: int):
            if depth > downstream_depth or key not in self.nodes:
                return
            nodes_to_include.add(key)
            for downstream_key in self.nodes[key].downstream:
                collect_downstream(downstream_key, depth + 1)

        collect_upstream(center_node.identifier, 0)
        collect_downstream(center_node.identifier, 0)

        # Copy nodes to subgraph
        for key in nodes_to_include:
            if key in self.nodes:
                original = self.nodes[key]
                subgraph.nodes[key] = LineageNode(
                    table=original.table,
                    schema=original.schema,
                    database=original.database,
                    node_type=original.node_type,
                    depth=original.depth,
                    upstream=[u for u in original.upstream if u in nodes_to_include],
                    downstream=[d for d in original.downstream if d in nodes_to_include],
                    metadata=original.metadata.copy(),
                )

        # Recompute metrics for subgraph
        if subgraph.nodes:
            subgraph._compute_node_metrics()
            subgraph._identify_special_nodes()
            subgraph._built = True

        return subgraph

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary for serialization."""
        return {
            "nodes": {key: node.to_dict() for key, node in self.nodes.items()},
            "roots": self._roots,
            "leaves": self._leaves,
            "orphans": self._orphans,
            "max_depth": self._max_depth,
            "critical_paths": self._critical_paths,
            "stats": {
                "total_nodes": len(self.nodes),
                "total_roots": len(self._roots),
                "total_leaves": len(self._leaves),
                "total_orphans": len(self._orphans),
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph."""
        node_types: Dict[str, int] = {}
        for node in self.nodes.values():
            node_types[node.node_type] = node_types.get(node.node_type, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_roots": len(self._roots),
            "total_leaves": len(self._leaves),
            "total_orphans": len(self._orphans),
            "max_depth": self._max_depth,
            "critical_paths_count": len(self._critical_paths),
            "node_type_distribution": node_types,
        }

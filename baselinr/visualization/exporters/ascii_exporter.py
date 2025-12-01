"""
ASCII art exporter for lineage graphs.

Generates terminal-friendly tree visualizations using box-drawing characters.
"""

from typing import Dict, List, Set

from ..graph_builder import LineageGraph, LineageNode

try:
    import colorama
    from colorama import Fore, Style

    colorama.init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

    # Dummy color constants for when colorama is not available
    if not HAS_COLOR:

        class Fore:  # type: ignore[no-redef]
            RED = ""
            YELLOW = ""
            GREEN = ""
            CYAN = ""
            WHITE = ""

        class Style:  # type: ignore[no-redef]
            RESET_ALL = ""


class ASCIIExporter:
    """
    Export lineage graphs to ASCII tree format.

    Creates terminal-friendly visualizations using box-drawing characters.
    """

    def __init__(
        self,
        use_color: bool = True,
        orientation: str = "vertical",
        indent: int = 4,
    ):
        """
        Initialize ASCII exporter.

        Args:
            use_color: Whether to use ANSI colors (requires colorama)
            orientation: 'vertical' or 'horizontal' tree layout
            indent: Number of spaces for indentation
        """
        self.use_color = use_color and HAS_COLOR
        self.orientation = orientation
        self.indent = indent

    def export(self, graph: LineageGraph) -> str:
        """
        Export graph to ASCII tree format.

        Args:
            graph: LineageGraph to export

        Returns:
            ASCII tree as string

        Example:
            >>> exporter = ASCIIExporter(use_color=True)
            >>> ascii_tree = exporter.export(graph)
            >>> print(ascii_tree)
        """
        if not graph.nodes:
            return "Empty graph"

        # Find root node
        root = None
        for node in graph.nodes:
            if node.metadata.get("is_root"):
                root = node
                break

        if not root:
            # Use first node as root
            root = graph.nodes[0]

        # Build adjacency map
        children_map = self._build_adjacency_map(graph)

        # Generate tree
        lines: List[str] = []
        visited: Set[str] = set()

        self._render_node_tree(root, graph, children_map, visited, lines, prefix="", is_last=True)

        return "\n".join(lines)

    def export_table(self, graph: LineageGraph) -> str:
        """
        Export graph as a simple table format.

        Args:
            graph: LineageGraph to export

        Returns:
            ASCII table as string
        """
        if not graph.nodes:
            return "Empty graph"

        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("LINEAGE GRAPH")
        lines.append("=" * 80)
        lines.append("")

        # Tables
        lines.append("NODES:")
        lines.append("-" * 80)

        for node in graph.nodes:
            status = ""
            if self.use_color:
                if node.metadata.get("has_drift"):
                    severity = node.metadata.get("drift_severity", "low")
                    if severity == "high":
                        status = f"{Fore.RED}[DRIFT: HIGH]{Style.RESET_ALL}"
                    elif severity == "medium":
                        status = f"{Fore.YELLOW}[DRIFT: MEDIUM]{Style.RESET_ALL}"
                    else:
                        status = f"{Fore.YELLOW}[DRIFT: LOW]{Style.RESET_ALL}"
                elif node.metadata.get("is_root"):
                    status = f"{Fore.CYAN}[ROOT]{Style.RESET_ALL}"
            else:
                if node.metadata.get("has_drift"):
                    severity = node.metadata.get("drift_severity", "low")
                    status = f"[DRIFT: {severity.upper()}]"
                elif node.metadata.get("is_root"):
                    status = "[ROOT]"

            lines.append(f"  {node.label} ({node.type}) {status}")

        lines.append("")
        lines.append("EDGES:")
        lines.append("-" * 80)

        for edge in graph.edges:
            confidence_str = f"[{edge.confidence:.2f}]" if edge.confidence < 1.0 else ""
            lines.append(
                f"  {edge.source} → {edge.target} " f"({edge.relationship_type}) {confidence_str}"
            )

        lines.append("=" * 80)

        return "\n".join(lines)

    def _render_node_tree(
        self,
        node: LineageNode,
        graph: LineageGraph,
        children_map: Dict[str, List[str]],
        visited: Set[str],
        lines: List[str],
        prefix: str,
        is_last: bool,
    ) -> None:
        """Recursively render node and its children as a tree."""
        # Avoid cycles
        if node.id in visited:
            return
        visited.add(node.id)

        # Determine tree characters
        if prefix == "":
            # Root node
            connector = ""
            new_prefix = ""
        else:
            connector = "└── " if is_last else "├── "
            new_prefix = prefix + ("    " if is_last else "│   ")

        # Format node label with color and metadata
        label = node.label

        if self.use_color:
            if node.metadata.get("has_drift"):
                severity = node.metadata.get("drift_severity", "low")
                if severity == "high":
                    label = f"{Fore.RED}{label}{Style.RESET_ALL}"
                elif severity == "medium":
                    label = f"{Fore.YELLOW}{label}{Style.RESET_ALL}"
                else:
                    label = f"{Fore.YELLOW}{label}{Style.RESET_ALL}"
            elif node.metadata.get("is_root"):
                label = f"{Fore.CYAN}{label}{Style.RESET_ALL}"

        # Add metadata annotations
        annotations = []
        if node.schema:
            annotations.append(f"schema: {node.schema}")
        if node.type == "column":
            annotations.append("column")

        if annotations:
            label += f" ({', '.join(annotations)})"

        lines.append(f"{prefix}{connector}{label}")

        # Render children
        children = children_map.get(node.id, [])
        for i, child_id in enumerate(children):
            child_node = graph.get_node_by_id(child_id)
            if child_node:
                self._render_node_tree(
                    child_node,
                    graph,
                    children_map,
                    visited,
                    lines,
                    new_prefix,
                    is_last=(i == len(children) - 1),
                )

    def _build_adjacency_map(self, graph: LineageGraph) -> Dict[str, List[str]]:
        """Build map of node ID to list of child node IDs."""
        adjacency: Dict[str, List[str]] = {}

        # Determine direction based on graph.direction
        if graph.direction == "downstream":
            # Source points to target (parent -> child)
            for edge in graph.edges:
                if edge.source not in adjacency:
                    adjacency[edge.source] = []
                adjacency[edge.source].append(edge.target)

        elif graph.direction == "upstream":
            # Target points to source (child -> parent, reversed for display)
            for edge in graph.edges:
                if edge.target not in adjacency:
                    adjacency[edge.target] = []
                adjacency[edge.target].append(edge.source)

        else:  # both
            # Show both directions, prefer downstream from root
            for edge in graph.edges:
                # Add both directions
                if edge.source not in adjacency:
                    adjacency[edge.source] = []
                adjacency[edge.source].append(edge.target)

        return adjacency

    def export_simple(self, graph: LineageGraph) -> str:
        """
        Export as simple text list (no tree structure).

        Args:
            graph: LineageGraph to export

        Returns:
            Simple list as string
        """
        lines = []

        for node in graph.nodes:
            indent_level = node.metadata.get("depth", 0)
            indent_str = "  " * indent_level

            symbol = "●" if node.metadata.get("is_root") else "○"

            lines.append(f"{indent_str}{symbol} {node.label}")

        return "\n".join(lines)

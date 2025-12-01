"""
Layout algorithms for lineage graph visualization.

Provides various layout strategies for positioning nodes in a 2D space.
"""

import math
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from .graph_builder import LineageGraph, LineageNode


class LayoutAlgorithm(ABC):
    """Base class for layout algorithms."""

    @abstractmethod
    def calculate_positions(self, graph: LineageGraph) -> Dict[str, Tuple[float, float]]:
        """
        Calculate 2D positions for all nodes in the graph.

        Args:
            graph: LineageGraph to layout

        Returns:
            Dictionary mapping node IDs to (x, y) tuples
        """
        pass


class HierarchicalLayout(LayoutAlgorithm):
    """
    Hierarchical layout for directed graphs.

    Places nodes in layers based on their depth, with upstream nodes at the top
    and downstream nodes at the bottom (or left-to-right for horizontal orientation).
    """

    def __init__(
        self,
        layer_spacing: float = 200.0,
        node_spacing: float = 150.0,
        orientation: str = "vertical",
    ):
        """
        Initialize hierarchical layout.

        Args:
            layer_spacing: Vertical spacing between layers
            node_spacing: Horizontal spacing between nodes in same layer
            orientation: 'vertical' (top-down) or 'horizontal' (left-right)
        """
        self.layer_spacing = layer_spacing
        self.node_spacing = node_spacing
        self.orientation = orientation

    def calculate_positions(self, graph: LineageGraph) -> Dict[str, Tuple[float, float]]:
        """Calculate hierarchical layout positions."""
        # Group nodes by depth
        layers: Dict[int, List[LineageNode]] = {}

        for node in graph.nodes:
            depth = node.metadata.get("depth", 0)

            # For root node, place at depth 0
            if node.metadata.get("is_root"):
                depth = 0

            if depth not in layers:
                layers[depth] = []
            layers[depth].append(node)

        # Calculate positions
        positions: Dict[str, Tuple[float, float]] = {}

        for depth, nodes_in_layer in sorted(layers.items()):
            layer_width = (len(nodes_in_layer) - 1) * self.node_spacing
            start_x = -layer_width / 2  # Center the layer

            for i, node in enumerate(nodes_in_layer):
                x = start_x + i * self.node_spacing
                y = depth * self.layer_spacing

                if self.orientation == "horizontal":
                    # Swap x and y for horizontal layout
                    positions[node.id] = (y, x)
                else:
                    positions[node.id] = (x, y)

        return positions


class CircularLayout(LayoutAlgorithm):
    """
    Circular layout for showing table clusters.

    Arranges nodes in a circle, with the root node at the center.
    """

    def __init__(self, radius: float = 300.0, center: Tuple[float, float] = (0, 0)):
        """
        Initialize circular layout.

        Args:
            radius: Radius of the circle
            center: Center point (x, y)
        """
        self.radius = radius
        self.center = center

    def calculate_positions(self, graph: LineageGraph) -> Dict[str, Tuple[float, float]]:
        """Calculate circular layout positions."""
        positions: Dict[str, Tuple[float, float]] = {}

        # Place root node at center
        root_node = None
        non_root_nodes = []

        for node in graph.nodes:
            if node.metadata.get("is_root"):
                root_node = node
            else:
                non_root_nodes.append(node)

        if root_node:
            positions[root_node.id] = self.center

        # Arrange other nodes in a circle
        if non_root_nodes:
            angle_step = 2 * math.pi / len(non_root_nodes)

            for i, node in enumerate(non_root_nodes):
                angle = i * angle_step
                x = self.center[0] + self.radius * math.cos(angle)
                y = self.center[1] + self.radius * math.sin(angle)
                positions[node.id] = (x, y)

        return positions


class ForceDirectedLayout(LayoutAlgorithm):
    """
    Force-directed layout for complex relationships.

    Uses a physics simulation to position nodes, treating edges as springs
    and nodes as repelling charges.
    """

    def __init__(
        self,
        iterations: int = 50,
        spring_strength: float = 0.1,
        repulsion_strength: float = 1000.0,
        damping: float = 0.9,
    ):
        """
        Initialize force-directed layout.

        Args:
            iterations: Number of simulation iterations
            spring_strength: Strength of attractive spring forces
            repulsion_strength: Strength of repulsive forces between nodes
            damping: Damping factor to stabilize simulation (0-1)
        """
        self.iterations = iterations
        self.spring_strength = spring_strength
        self.repulsion_strength = repulsion_strength
        self.damping = damping

    def calculate_positions(self, graph: LineageGraph) -> Dict[str, Tuple[float, float]]:
        """Calculate force-directed layout positions."""
        # Initialize random positions
        import random

        positions: Dict[str, Tuple[float, float]] = {}
        velocities: Dict[str, Tuple[float, float]] = {}

        for node in graph.nodes:
            # Random initial position
            x = random.uniform(-200, 200)
            y = random.uniform(-200, 200)

            # Root node starts at center
            if node.metadata.get("is_root"):
                x, y = 0, 0

            positions[node.id] = (x, y)
            velocities[node.id] = (0.0, 0.0)

        # Build edge index for faster lookup
        edges_by_node: Dict[str, List[str]] = {}
        for edge in graph.edges:
            if edge.source not in edges_by_node:
                edges_by_node[edge.source] = []
            if edge.target not in edges_by_node:
                edges_by_node[edge.target] = []
            edges_by_node[edge.source].append(edge.target)
            edges_by_node[edge.target].append(edge.source)

        # Simulation loop
        for _ in range(self.iterations):
            forces: Dict[str, Tuple[float, float]] = {node.id: (0.0, 0.0) for node in graph.nodes}

            # Calculate repulsive forces between all node pairs
            for i, node_a in enumerate(graph.nodes):
                for node_b in graph.nodes[i + 1 :]:
                    pos_a = positions[node_a.id]
                    pos_b = positions[node_b.id]

                    dx = pos_a[0] - pos_b[0]
                    dy = pos_a[1] - pos_b[1]
                    distance = math.sqrt(dx * dx + dy * dy)

                    if distance > 0:
                        # Repulsive force (Coulomb's law)
                        force = self.repulsion_strength / (distance * distance)
                        fx = (dx / distance) * force
                        fy = (dy / distance) * force

                        forces[node_a.id] = (
                            forces[node_a.id][0] + fx,
                            forces[node_a.id][1] + fy,
                        )
                        forces[node_b.id] = (
                            forces[node_b.id][0] - fx,
                            forces[node_b.id][1] - fy,
                        )

            # Calculate attractive forces for connected nodes
            for edge in graph.edges:
                pos_source = positions[edge.source]
                pos_target = positions[edge.target]

                dx = pos_target[0] - pos_source[0]
                dy = pos_target[1] - pos_source[1]
                distance = math.sqrt(dx * dx + dy * dy)

                if distance > 0:
                    # Attractive force (Hooke's law)
                    force = self.spring_strength * distance
                    fx = (dx / distance) * force
                    fy = (dy / distance) * force

                    forces[edge.source] = (
                        forces[edge.source][0] + fx,
                        forces[edge.source][1] + fy,
                    )
                    forces[edge.target] = (
                        forces[edge.target][0] - fx,
                        forces[edge.target][1] - fy,
                    )

            # Update velocities and positions
            for node in graph.nodes:
                # Skip root node (keep it centered)
                if node.metadata.get("is_root"):
                    continue

                # Update velocity
                vx, vy = velocities[node.id]
                fx, fy = forces[node.id]

                vx = (vx + fx) * self.damping
                vy = (vy + fy) * self.damping

                velocities[node.id] = (vx, vy)

                # Update position
                x, y = positions[node.id]
                x += vx
                y += vy

                positions[node.id] = (x, y)

        return positions


class GridLayout(LayoutAlgorithm):
    """
    Simple grid layout.

    Arranges nodes in a regular grid pattern.
    """

    def __init__(self, cell_width: float = 200.0, cell_height: float = 150.0):
        """
        Initialize grid layout.

        Args:
            cell_width: Width of each grid cell
            cell_height: Height of each grid cell
        """
        self.cell_width = cell_width
        self.cell_height = cell_height

    def calculate_positions(self, graph: LineageGraph) -> Dict[str, Tuple[float, float]]:
        """Calculate grid layout positions."""
        positions: Dict[str, Tuple[float, float]] = {}

        # Calculate grid dimensions
        n_nodes = len(graph.nodes)
        cols = math.ceil(math.sqrt(n_nodes))

        for i, node in enumerate(graph.nodes):
            row = i // cols
            col = i % cols

            x = col * self.cell_width
            y = row * self.cell_height

            positions[node.id] = (x, y)

        return positions

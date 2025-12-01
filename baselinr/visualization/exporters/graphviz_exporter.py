"""
Graphviz DOT format exporter for lineage graphs.

Generates DOT files that can be rendered to images using Graphviz.
"""

import subprocess
import tempfile
from pathlib import Path

from ..graph_builder import LineageGraph


class GraphvizExporter:
    """
    Export lineage graphs to Graphviz DOT format.

    Supports hierarchical layout and various output image formats.
    """

    def __init__(
        self,
        rankdir: str = "TB",
        node_shape: str = "box",
        edge_style: str = "solid",
    ):
        """
        Initialize Graphviz exporter.

        Args:
            rankdir: Graph direction - 'TB' (top-bottom), 'LR' (left-right),
                     'BT' (bottom-top), or 'RL' (right-left)
            node_shape: Default node shape ('box', 'ellipse', 'circle', etc.)
            edge_style: Default edge style ('solid', 'dashed', 'dotted')
        """
        self.rankdir = rankdir
        self.node_shape = node_shape
        self.edge_style = edge_style

    def export_dot(self, graph: LineageGraph) -> str:
        """
        Export graph to DOT format string.

        Args:
            graph: LineageGraph to export

        Returns:
            DOT format as string

        Example:
            >>> exporter = GraphvizExporter(rankdir="LR")
            >>> dot_code = exporter.export_dot(graph)
            >>> with open("lineage.dot", "w") as f:
            ...     f.write(dot_code)
        """
        lines = ["digraph lineage {"]

        # Graph attributes
        lines.append(f"    rankdir={self.rankdir};")
        lines.append('    node [fontname="Helvetica", fontsize=10];')
        lines.append('    edge [fontname="Helvetica", fontsize=8];')
        lines.append("")

        # Add nodes
        for node in graph.nodes:
            node_id = self._sanitize_id(node.id)
            label = node.label

            # Node attributes
            attrs = []

            # Shape based on type
            if node.type == "column":
                attrs.append("shape=ellipse")
            else:
                attrs.append(f"shape={self.node_shape}")

            # Color based on drift status
            if node.metadata.get("has_drift"):
                severity = node.metadata.get("drift_severity", "low")
                if severity == "high":
                    attrs.append('fillcolor="#ff8787"')
                    attrs.append('style="filled"')
                    attrs.append("penwidth=3")
                elif severity == "medium":
                    attrs.append('fillcolor="#ffd966"')
                    attrs.append('style="filled"')
                    attrs.append("penwidth=2")
                else:
                    attrs.append('fillcolor="#fff4e6"')
                    attrs.append('style="filled"')
            elif node.metadata.get("is_root"):
                attrs.append('fillcolor="#d4edff"')
                attrs.append('style="filled,bold"')
                attrs.append("penwidth=2")
            else:
                attrs.append('fillcolor="#f0f0f0"')
                attrs.append('style="filled"')

            attrs.append(f'label="{label}"')

            attrs_str = ", ".join(attrs)
            lines.append(f"    {node_id} [{attrs_str}];")

        lines.append("")

        # Add edges
        for edge in graph.edges:
            source_id = self._sanitize_id(edge.source)
            target_id = self._sanitize_id(edge.target)

            # Edge attributes
            attrs = []

            # Label
            label = edge.relationship_type
            if edge.confidence < 1.0:
                label += f"\\n({edge.confidence:.2f})"
            attrs.append(f'label="{label}"')

            # Style based on confidence
            if edge.confidence >= 0.8:
                attrs.append("style=solid")
                attrs.append("penwidth=2")
            elif edge.confidence >= 0.5:
                attrs.append("style=dashed")
                attrs.append("penwidth=1.5")
            else:
                attrs.append("style=dotted")
                attrs.append("penwidth=1")

            # Color based on provider
            if edge.provider == "dbt":
                attrs.append('color="#4a90e2"')
            elif edge.provider == "sql_parser":
                attrs.append('color="#50c878"')
            else:
                attrs.append('color="#888888"')

            attrs_str = ", ".join(attrs)
            lines.append(f"    {source_id} -> {target_id} [{attrs_str}];")

        lines.append("}")

        return "\n".join(lines)

    def export_image(
        self,
        graph: LineageGraph,
        output_path: str,
        format: str = "svg",
        engine: str = "dot",
    ) -> bool:
        """
        Export graph to image file using Graphviz.

        Args:
            graph: LineageGraph to export
            output_path: Path to save the image
            format: Output format ('svg', 'png', 'pdf', etc.)
            engine: Graphviz layout engine ('dot', 'neato', 'fdp', 'circo', etc.)

        Returns:
            True if successful, False otherwise

        Example:
            >>> exporter = GraphvizExporter()
            >>> success = exporter.export_image(graph, "lineage.svg", format="svg")
            >>> if success:
            ...     print("Image saved successfully")

        Note:
            Requires Graphviz to be installed on the system.
        """
        # Check if Graphviz is available
        try:
            subprocess.run(
                [engine, "-V"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                f"Graphviz engine '{engine}' not found. "
                "Please install Graphviz: https://graphviz.org/download/"
            )

        # Generate DOT content
        dot_content = self.export_dot(graph)

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as tmp:
            tmp.write(dot_content)
            tmp_path = tmp.name

        try:
            # Run Graphviz to generate image
            subprocess.run(
                [engine, f"-T{format}", tmp_path, "-o", output_path],
                capture_output=True,
                text=True,
                check=True,
            )

            return True

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Graphviz rendering failed: {e.stderr}")

        finally:
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)

    def _sanitize_id(self, node_id: str) -> str:
        """Sanitize node ID for DOT syntax."""
        # Replace special characters and wrap in quotes
        sanitized = node_id.replace('"', '\\"')
        return f'"{sanitized}"'

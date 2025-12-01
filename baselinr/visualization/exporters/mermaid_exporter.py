"""
Mermaid diagram exporter for lineage graphs.

Generates Mermaid syntax for creating diagrams in markdown or documentation.
"""

from typing import Dict, List

from ..graph_builder import LineageGraph, LineageNode


class MermaidExporter:
    """
    Export lineage graphs to Mermaid diagram format.

    Mermaid is a popular diagramming tool that uses simple text syntax.
    """

    def __init__(self, direction: str = "TD", include_legend: bool = True):
        """
        Initialize Mermaid exporter.

        Args:
            direction: Diagram direction - 'TD' (top-down), 'LR' (left-right),
                       'BT' (bottom-top), or 'RL' (right-left)
            include_legend: Whether to include a legend in the diagram
        """
        self.direction = direction
        self.include_legend = include_legend

    def export(self, graph: LineageGraph) -> str:
        """
        Export graph to Mermaid diagram syntax.

        Args:
            graph: LineageGraph to export

        Returns:
            Mermaid diagram as string

        Example:
            >>> exporter = MermaidExporter(direction="LR")
            >>> mermaid_code = exporter.export(graph)
            >>> with open("lineage.md", "w") as f:
            ...     f.write(f"```mermaid\\n{mermaid_code}\\n```")
        """
        lines = [f"graph {self.direction}"]

        # Add nodes with styling
        for node in graph.nodes:
            node_id = self._sanitize_id(node.id)
            label = node.label

            # Add metadata to label
            if node.metadata.get("is_root"):
                label = f"**{label}**"

            # Choose shape based on node type and status
            if node.metadata.get("is_root"):
                shape = f"[{label}]"  # Rectangle for root
            elif node.type == "column":
                shape = f"({label})"  # Rounded for columns
            else:
                shape = f"[{label}]"  # Rectangle for tables

            lines.append(f"    {node_id}{shape}")

            # Add style class based on drift status
            if node.metadata.get("has_drift"):
                severity = node.metadata.get("drift_severity", "low")
                lines.append(f"    class {node_id} drift_{severity}")

        # Add edges
        for edge in graph.edges:
            source_id = self._sanitize_id(edge.source)
            target_id = self._sanitize_id(edge.target)

            # Edge label
            label = edge.relationship_type
            if edge.confidence < 1.0:
                label += f" ({edge.confidence:.2f})"

            # Edge style based on confidence
            if edge.confidence >= 0.8:
                arrow = "-->|"  # Solid line
            elif edge.confidence >= 0.5:
                arrow = "-.->|"  # Dotted line
            else:
                arrow = "-.-|"  # Very dotted line

            lines.append(f"    {source_id} {arrow}{label}|{target_id}")

        # Add style definitions
        lines.append("")
        lines.append("    %% Styles")
        lines.append("    classDef drift_high fill:#ff8787,stroke:#ff0000,stroke-width:3px")
        lines.append("    classDef drift_medium fill:#ffd966,stroke:#ff8800,stroke-width:2px")
        lines.append("    classDef drift_low fill:#fff4e6,stroke:#ffbb33,stroke-width:1px")
        lines.append("    classDef healthy fill:#d4f1d4,stroke:#4caf50,stroke-width:1px")

        # Add legend if requested
        if self.include_legend:
            lines.append("")
            lines.append("    %% Legend")
            lines.append("    subgraph Legend")
            lines.append("        L1[Table]")
            lines.append("        L2(Column)")
            lines.append("        L3[High Drift]")
            lines.append("        class L3 drift_high")
            lines.append("    end")

        return "\n".join(lines)

    def export_with_schema_grouping(self, graph: LineageGraph) -> str:
        """
        Export graph with schema-based subgraphs.

        Args:
            graph: LineageGraph to export

        Returns:
            Mermaid diagram with schema grouping
        """
        lines = [f"graph {self.direction}"]

        # Group nodes by schema
        schemas: Dict[str, List[LineageNode]] = {}
        for node in graph.nodes:
            schema = node.schema or "default"
            if schema not in schemas:
                schemas[schema] = []
            schemas[schema].append(node)

        # Create subgraphs for each schema
        for schema, nodes in schemas.items():
            lines.append(f"    subgraph {schema}")

            for node in nodes:
                node_id = self._sanitize_id(node.id)
                label = node.label

                if node.metadata.get("is_root"):
                    shape = f"[**{label}**]"
                elif node.type == "column":
                    shape = f"({label})"
                else:
                    shape = f"[{label}]"

                lines.append(f"        {node_id}{shape}")

            lines.append("    end")

        # Add edges
        lines.append("")
        for edge in graph.edges:
            source_id = self._sanitize_id(edge.source)
            target_id = self._sanitize_id(edge.target)
            label = edge.relationship_type

            arrow = "-->"
            if edge.confidence < 0.8:
                arrow = "-.->  "

            lines.append(f"    {source_id} {arrow}|{label}| {target_id}")

        return "\n".join(lines)

    def _sanitize_id(self, node_id: str) -> str:
        """Sanitize node ID for Mermaid syntax."""
        # Replace special characters with underscores
        return node_id.replace(".", "_").replace("-", "_").replace(" ", "_")

    def _get_node_styles(self, graph: LineageGraph) -> Dict[str, str]:
        """Get style mapping for nodes based on their status."""
        styles = {}

        for node in graph.nodes:
            if node.metadata.get("has_drift"):
                severity = node.metadata.get("drift_severity", "low")
                styles[node.id] = f"drift_{severity}"
            else:
                styles[node.id] = "healthy"

        return styles

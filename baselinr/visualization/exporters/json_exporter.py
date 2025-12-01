"""
JSON exporters for lineage graphs.

Supports multiple JSON formats including Cytoscape.js, D3.js, and generic formats.
"""

import json
from typing import Any, Dict, List, Optional

from ..graph_builder import LineageGraph
from ..layout import LayoutAlgorithm


class JSONExporter:
    """
    Export lineage graphs to various JSON formats.

    Supports Cytoscape.js, D3.js, and generic JSON formats.
    """

    def __init__(self, layout: Optional[LayoutAlgorithm] = None):
        """
        Initialize JSON exporter.

        Args:
            layout: Optional layout algorithm to compute node positions
        """
        self.layout = layout

    def export_cytoscape(self, graph: LineageGraph, pretty: bool = True) -> str:
        """
        Export graph to Cytoscape.js format.

        Args:
            graph: LineageGraph to export
            pretty: Whether to pretty-print JSON

        Returns:
            Cytoscape.js JSON as string

        Example:
            >>> exporter = JSONExporter()
            >>> cytoscape_json = exporter.export_cytoscape(graph)
            >>> with open("lineage.json", "w") as f:
            ...     f.write(cytoscape_json)
        """
        elements: List[Dict[str, Any]] = []

        # Add nodes
        for node in graph.nodes:
            node_data: Dict[str, Any] = {
                "data": {
                    "id": node.id,
                    "label": node.label,
                    "type": node.type,
                }
            }

            # Add optional fields
            if node.schema:
                node_data["data"]["schema"] = node.schema
            if node.table:
                node_data["data"]["table"] = node.table
            if node.column:
                node_data["data"]["column"] = node.column

            # Add metadata
            if node.metadata:
                node_data["data"]["metadata"] = node.metadata

            # Add position if layout provided
            if self.layout:
                positions = self.layout.calculate_positions(graph)
                if node.id in positions:
                    x, y = positions[node.id]
                    node_data["position"] = {"x": x, "y": y}

            # Add classes for styling
            classes: List[str] = []
            if node.metadata.get("is_root"):
                classes.append("root")
            if node.metadata.get("has_drift"):
                severity = node.metadata.get("drift_severity", "low")
                classes.append(f"drift-{severity}")

            if classes:
                node_data["classes"] = " ".join(classes)

            elements.append(node_data)

        # Add edges
        for edge in graph.edges:
            edge_data: Dict[str, Any] = {
                "data": {
                    "id": f"{edge.source}-{edge.target}",
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.relationship_type,
                    "confidence": edge.confidence,
                }
            }

            if edge.transformation:
                edge_data["data"]["transformation"] = edge.transformation

            if edge.provider:
                edge_data["data"]["provider"] = edge.provider

            # Add metadata
            if edge.metadata:
                edge_data["data"]["metadata"] = edge.metadata

            # Add classes for styling
            classes_edge: List[str] = []
            if edge.confidence < 0.5:
                classes_edge.append("low-confidence")
            elif edge.confidence < 0.8:
                classes_edge.append("medium-confidence")
            else:
                classes_edge.append("high-confidence")

            if classes_edge:
                edge_data["classes"] = " ".join(classes_edge)

            elements.append(edge_data)

        result = {
            "elements": elements,
            "metadata": {
                "root_id": graph.root_id,
                "direction": graph.direction,
                "node_count": len(graph.nodes),
                "edge_count": len(graph.edges),
            },
        }

        indent = 2 if pretty else None
        return json.dumps(result, indent=indent)

    def export_d3(self, graph: LineageGraph, pretty: bool = True) -> str:
        """
        Export graph to D3.js force-directed format.

        Args:
            graph: LineageGraph to export
            pretty: Whether to pretty-print JSON

        Returns:
            D3.js JSON as string

        Example:
            >>> exporter = JSONExporter()
            >>> d3_json = exporter.export_d3(graph)
        """
        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []

        # Create node index map
        node_index = {node.id: i for i, node in enumerate(graph.nodes)}

        # Add nodes
        for node in graph.nodes:
            node_data: Dict[str, Any] = {
                "id": node.id,
                "label": node.label,
                "type": node.type,
            }

            if node.schema:
                node_data["schema"] = node.schema
            if node.table:
                node_data["table"] = node.table
            if node.column:
                node_data["column"] = node.column

            # Add metadata
            node_data["metadata"] = node.metadata or {}

            # Add group for coloring
            if node.metadata and node.metadata.get("has_drift"):
                node_data["group"] = "drift"
            elif node.metadata and node.metadata.get("is_root"):
                node_data["group"] = "root"
            else:
                node_data["group"] = "normal"

            nodes.append(node_data)

        # Add links (edges)
        for edge in graph.edges:
            link_data = {
                "source": node_index.get(edge.source, 0),
                "target": node_index.get(edge.target, 0),
                "label": edge.relationship_type,
                "value": edge.confidence,  # Used for link strength
            }

            if edge.provider:
                link_data["provider"] = edge.provider

            links.append(link_data)

        result = {
            "nodes": nodes,
            "links": links,
            "metadata": {
                "root_id": graph.root_id,
                "direction": graph.direction,
            },
        }

        indent = 2 if pretty else None
        return json.dumps(result, indent=indent)

    def export_generic(self, graph: LineageGraph, pretty: bool = True) -> str:
        """
        Export graph to generic JSON format.

        This format directly serializes the graph structure without
        transformation for specific visualization libraries.

        Args:
            graph: LineageGraph to export
            pretty: Whether to pretty-print JSON

        Returns:
            Generic JSON as string
        """
        result = graph.to_dict()

        indent = 2 if pretty else None
        return json.dumps(result, indent=indent, default=str)

    def export_networkx(self, graph: LineageGraph) -> Dict[str, Any]:
        """
        Export graph to NetworkX-compatible dictionary format.

        Args:
            graph: LineageGraph to export

        Returns:
            Dictionary compatible with NetworkX's node-link format

        Example:
            >>> exporter = JSONExporter()
            >>> nx_data = exporter.export_networkx(graph)
            >>> import networkx as nx
            >>> G = nx.node_link_graph(nx_data)
        """
        nodes = []
        links = []

        # Add nodes
        for node in graph.nodes:
            node_data = {
                "id": node.id,
                **node.to_dict(),
            }
            nodes.append(node_data)

        # Add links
        for edge in graph.edges:
            link_data = {
                "source": edge.source,
                "target": edge.target,
                **edge.to_dict(),
            }
            links.append(link_data)

        return {
            "directed": True,
            "multigraph": False,
            "graph": {
                "root_id": graph.root_id,
                "direction": graph.direction,
            },
            "nodes": nodes,
            "links": links,
        }

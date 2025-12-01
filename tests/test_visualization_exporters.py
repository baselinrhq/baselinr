"""
Tests for lineage exporters.
"""

import pytest

from baselinr.visualization.graph_builder import LineageGraph, LineageNode, LineageEdge
from baselinr.visualization.exporters import (
    MermaidExporter,
    JSONExporter,
    ASCIIExporter,
)


class TestMermaidExporter:
    """Test MermaidExporter."""

    def test_export_simple_graph(self):
        """Test exporting a simple graph to Mermaid."""
        nodes = [
            LineageNode(
                id="public.customers",
                type="table",
                label="customers",
                metadata={"is_root": True},
            ),
            LineageNode(
                id="public.orders",
                type="table",
                label="orders",
            ),
        ]

        edges = [
            LineageEdge(
                source="public.customers",
                target="public.orders",
                relationship_type="derived_from",
                confidence=0.95,
            )
        ]

        graph = LineageGraph(nodes=nodes, edges=edges, root_id="public.customers")

        exporter = MermaidExporter(direction="TD", include_legend=False)
        output = exporter.export(graph)

        assert "graph TD" in output
        assert "customers" in output
        assert "orders" in output
        assert "derived_from" in output

    def test_sanitize_id(self):
        """Test ID sanitization for Mermaid."""
        exporter = MermaidExporter()

        # Replace dots with underscores
        assert exporter._sanitize_id("public.customers") == "public_customers"
        assert exporter._sanitize_id("my-table") == "my_table"
        assert exporter._sanitize_id("my table") == "my_table"


class TestJSONExporter:
    """Test JSONExporter."""

    def test_export_cytoscape(self):
        """Test exporting to Cytoscape.js format."""
        import json

        node = LineageNode(
            id="public.customers",
            type="table",
            label="customers",
        )

        edge = LineageEdge(
            source="public.customers",
            target="public.orders",
            relationship_type="derived_from",
        )

        graph = LineageGraph(nodes=[node], edges=[edge])

        exporter = JSONExporter()
        output = exporter.export_cytoscape(graph, pretty=False)

        data = json.loads(output)
        assert "elements" in data
        assert len(data["elements"]) == 2  # 1 node + 1 edge

    def test_export_d3(self):
        """Test exporting to D3.js format."""
        import json

        nodes = [
            LineageNode(id="A", type="table", label="A"),
            LineageNode(id="B", type="table", label="B"),
        ]

        edges = [
            LineageEdge(source="A", target="B", relationship_type="test"),
        ]

        graph = LineageGraph(nodes=nodes, edges=edges)

        exporter = JSONExporter()
        output = exporter.export_d3(graph, pretty=False)

        data = json.loads(output)
        assert "nodes" in data
        assert "links" in data
        assert len(data["nodes"]) == 2
        assert len(data["links"]) == 1
        # Links should use indices
        assert data["links"][0]["source"] == 0
        assert data["links"][0]["target"] == 1

    def test_export_generic(self):
        """Test exporting to generic JSON format."""
        import json

        node = LineageNode(id="A", type="table", label="A")
        graph = LineageGraph(nodes=[node])

        exporter = JSONExporter()
        output = exporter.export_generic(graph, pretty=False)

        data = json.loads(output)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 1


class TestASCIIExporter:
    """Test ASCIIExporter."""

    def test_export_simple(self):
        """Test simple ASCII export."""
        nodes = [
            LineageNode(id="A", type="table", label="A", metadata={"depth": 0}),
            LineageNode(id="B", type="table", label="B", metadata={"depth": 1}),
        ]

        graph = LineageGraph(nodes=nodes)

        exporter = ASCIIExporter(use_color=False)
        output = exporter.export_simple(graph)

        assert "A" in output
        assert "B" in output

    def test_export_table(self):
        """Test table format export."""
        node = LineageNode(id="A", type="table", label="A")
        edge = LineageEdge(source="A", target="B", relationship_type="test")

        graph = LineageGraph(nodes=[node], edges=[edge])

        exporter = ASCIIExporter(use_color=False)
        output = exporter.export_table(graph)

        assert "LINEAGE GRAPH" in output
        assert "NODES:" in output
        assert "EDGES:" in output
        assert "A" in output

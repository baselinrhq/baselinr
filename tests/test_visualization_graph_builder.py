"""
Tests for lineage graph builder.
"""

import pytest
from unittest.mock import Mock, MagicMock

from baselinr.visualization.graph_builder import (
    LineageGraph,
    LineageGraphBuilder,
    LineageNode,
    LineageEdge,
)


class TestLineageNode:
    """Test LineageNode dataclass."""

    def test_create_table_node(self):
        """Test creating a table node."""
        node = LineageNode(
            id="public.customers",
            type="table",
            label="customers",
            schema="public",
            table="customers",
        )

        assert node.id == "public.customers"
        assert node.type == "table"
        assert node.label == "customers"
        assert node.schema == "public"
        assert node.table == "customers"

    def test_create_column_node(self):
        """Test creating a column node."""
        node = LineageNode(
            id="public.orders.customer_id",
            type="column",
            label="orders.customer_id",
            schema="public",
            table="orders",
            column="customer_id",
        )

        assert node.id == "public.orders.customer_id"
        assert node.type == "column"
        assert node.column == "customer_id"

    def test_node_to_dict(self):
        """Test node serialization."""
        node = LineageNode(
            id="public.customers",
            type="table",
            label="customers",
            schema="public",
            table="customers",
            metadata={"is_root": True},
        )

        data = node.to_dict()
        assert data["id"] == "public.customers"
        assert data["type"] == "table"
        assert data["metadata"]["is_root"] is True


class TestLineageEdge:
    """Test LineageEdge dataclass."""

    def test_create_edge(self):
        """Test creating an edge."""
        edge = LineageEdge(
            source="public.customers",
            target="public.orders",
            relationship_type="derived_from",
            confidence=0.95,
        )

        assert edge.source == "public.customers"
        assert edge.target == "public.orders"
        assert edge.relationship_type == "derived_from"
        assert edge.confidence == 0.95

    def test_edge_to_dict(self):
        """Test edge serialization."""
        edge = LineageEdge(
            source="public.customers",
            target="public.orders",
            relationship_type="derived_from",
            confidence=0.95,
            provider="dbt",
        )

        data = edge.to_dict()
        assert data["source"] == "public.customers"
        assert data["target"] == "public.orders"
        assert data["confidence"] == 0.95
        assert data["provider"] == "dbt"


class TestLineageGraph:
    """Test LineageGraph dataclass."""

    def test_create_graph(self):
        """Test creating a graph."""
        nodes = [
            LineageNode(
                id="public.customers",
                type="table",
                label="customers",
                schema="public",
                table="customers",
            ),
            LineageNode(
                id="public.orders",
                type="table",
                label="orders",
                schema="public",
                table="orders",
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

        graph = LineageGraph(
            nodes=nodes,
            edges=edges,
            root_id="public.customers",
            direction="downstream",
        )

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.root_id == "public.customers"

    def test_get_node_by_id(self):
        """Test getting node by ID."""
        node = LineageNode(
            id="public.customers",
            type="table",
            label="customers",
        )

        graph = LineageGraph(nodes=[node])
        found = graph.get_node_by_id("public.customers")

        assert found is not None
        assert found.id == "public.customers"

    def test_get_node_by_id_not_found(self):
        """Test getting non-existent node."""
        graph = LineageGraph(nodes=[])
        found = graph.get_node_by_id("nonexistent")

        assert found is None

    def test_filter_by_confidence(self):
        """Test filtering graph by confidence threshold."""
        nodes = [
            LineageNode(id="A", type="table", label="A"),
            LineageNode(id="B", type="table", label="B"),
            LineageNode(id="C", type="table", label="C"),
        ]

        edges = [
            LineageEdge(source="A", target="B", relationship_type="test", confidence=0.9),
            LineageEdge(source="A", target="C", relationship_type="test", confidence=0.4),
        ]

        graph = LineageGraph(nodes=nodes, edges=edges, root_id="A")
        filtered = graph.filter_by_confidence(0.5)

        assert len(filtered.edges) == 1
        assert filtered.edges[0].target == "B"
        # Node C should be removed as it's no longer referenced
        assert len(filtered.nodes) == 2

    def test_graph_to_dict(self):
        """Test graph serialization."""
        node = LineageNode(id="A", type="table", label="A")
        edge = LineageEdge(source="A", target="B", relationship_type="test")

        graph = LineageGraph(
            nodes=[node],
            edges=[edge],
            root_id="A",
            direction="both",
        )

        data = graph.to_dict()
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 1
        assert data["root_id"] == "A"
        assert data["direction"] == "both"


class TestLineageGraphBuilder:
    """Test LineageGraphBuilder class."""

    def test_init(self):
        """Test builder initialization."""
        engine = Mock()
        builder = LineageGraphBuilder(engine)

        assert builder.engine == engine
        assert builder.lineage_table == "baselinr_lineage"

    def test_make_table_id(self):
        """Test table ID generation."""
        engine = Mock()
        builder = LineageGraphBuilder(engine)

        # With schema
        assert builder._make_table_id("public", "customers") == "public.customers"

        # Without schema
        assert builder._make_table_id(None, "customers") == "customers"

    def test_make_column_id(self):
        """Test column ID generation."""
        engine = Mock()
        builder = LineageGraphBuilder(engine)

        # With schema
        assert (
            builder._make_column_id("public", "orders", "customer_id")
            == "public.orders.customer_id"
        )

        # Without schema
        assert builder._make_column_id(None, "orders", "customer_id") == "orders.customer_id"


# Note: Full integration tests would require actual database setup
# These basic tests cover the data structures and core logic

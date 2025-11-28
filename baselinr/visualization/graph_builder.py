"""
Graph builder for lineage visualization.

Constructs graph data structures from lineage data stored in the database.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.engine import Engine

from ..query.lineage_client import LineageQueryClient

logger = logging.getLogger(__name__)


@dataclass
class LineageNode:
    """Represents a node in the lineage graph (table or column)."""

    id: str  # Unique identifier (e.g., "schema.table" or "schema.table.column")
    type: str  # 'table' or 'column'
    label: str  # Display name
    schema: Optional[str] = None
    table: Optional[str] = None
    column: Optional[str] = None
    database: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "schema": self.schema,
            "table": self.table,
            "column": self.column,
            "database": self.database,
            "metadata": self.metadata,
            "metrics": self.metrics,
        }


@dataclass
class LineageEdge:
    """Represents an edge in the lineage graph (relationship)."""

    source: str  # Source node ID
    target: str  # Target node ID
    relationship_type: str  # Type of relationship (e.g., 'derived_from', 'joined_with')
    confidence: float = 1.0
    transformation: Optional[str] = None
    provider: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source": self.source,
            "target": self.target,
            "relationship_type": self.relationship_type,
            "confidence": self.confidence,
            "transformation": self.transformation,
            "provider": self.provider,
            "metadata": self.metadata,
        }


@dataclass
class LineageGraph:
    """Complete lineage graph with nodes and edges."""

    nodes: List[LineageNode] = field(default_factory=list)
    edges: List[LineageEdge] = field(default_factory=list)
    root_id: Optional[str] = None
    direction: str = "both"  # 'upstream', 'downstream', or 'both'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "root_id": self.root_id,
            "direction": self.direction,
        }
    
    def get_node_by_id(self, node_id: str) -> Optional[LineageNode]:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def filter_by_confidence(self, min_confidence: float) -> "LineageGraph":
        """Return a new graph with edges filtered by minimum confidence."""
        filtered_edges = [e for e in self.edges if e.confidence >= min_confidence]
        
        # Get node IDs that are still referenced
        referenced_node_ids = set()
        for edge in filtered_edges:
            referenced_node_ids.add(edge.source)
            referenced_node_ids.add(edge.target)
        
        # Filter nodes to only those still referenced
        filtered_nodes = [
            n for n in self.nodes if n.id in referenced_node_ids or n.id == self.root_id
        ]
        
        return LineageGraph(
            nodes=filtered_nodes,
            edges=filtered_edges,
            root_id=self.root_id,
            direction=self.direction,
        )


class LineageGraphBuilder:
    """
    Builder for constructing lineage graphs from database.
    
    Queries lineage data and constructs graph structures with nodes and edges.
    """

    def __init__(
        self,
        engine: Engine,
        lineage_table: str = "baselinr_lineage",
        column_lineage_table: str = "baselinr_column_lineage",
    ):
        """
        Initialize graph builder.

        Args:
            engine: SQLAlchemy engine for database connection
            lineage_table: Name of table-level lineage table
            column_lineage_table: Name of column-level lineage table
        """
        self.engine = engine
        self.client = LineageQueryClient(engine, lineage_table)
        self.lineage_table = lineage_table
        self.column_lineage_table = column_lineage_table

    def build_table_graph(
        self,
        root_table: str,
        schema: Optional[str] = None,
        direction: str = "both",
        max_depth: int = 3,
        confidence_threshold: float = 0.0,
    ) -> LineageGraph:
        """
        Build table-level lineage graph.

        Args:
            root_table: Name of the root table
            schema: Optional schema name
            direction: Direction to traverse ('upstream', 'downstream', or 'both')
            max_depth: Maximum depth to traverse
            confidence_threshold: Minimum confidence score for edges (0.0 to 1.0)

        Returns:
            LineageGraph with table nodes and edges

        Example:
            >>> builder = LineageGraphBuilder(engine)
            >>> graph = builder.build_table_graph("customers", direction="both", max_depth=2)
            >>> print(f"Found {len(graph.nodes)} tables and {len(graph.edges)} relationships")
        """
        nodes_dict: Dict[str, LineageNode] = {}
        edges_list: List[LineageEdge] = []
        
        # Create root node
        root_id = self._make_table_id(schema, root_table)
        nodes_dict[root_id] = LineageNode(
            id=root_id,
            type="table",
            label=root_table,
            schema=schema,
            table=root_table,
            metadata={"is_root": True},
        )
        
        # Get upstream dependencies
        if direction in ("upstream", "both"):
            upstream_data = self.client.get_upstream_tables(
                root_table, schema_name=schema, max_depth=max_depth
            )
            self._process_table_lineage_data(
                upstream_data, nodes_dict, edges_list, is_upstream=True
            )
        
        # Get downstream dependencies
        if direction in ("downstream", "both"):
            downstream_data = self.client.get_downstream_tables(
                root_table, schema_name=schema, max_depth=max_depth
            )
            self._process_table_lineage_data(
                downstream_data, nodes_dict, edges_list, is_upstream=False
            )
        
        graph = LineageGraph(
            nodes=list(nodes_dict.values()),
            edges=edges_list,
            root_id=root_id,
            direction=direction,
        )
        
        # Filter by confidence if threshold > 0
        if confidence_threshold > 0:
            graph = graph.filter_by_confidence(confidence_threshold)
        
        return graph

    def build_column_graph(
        self,
        root_table: str,
        root_column: str,
        schema: Optional[str] = None,
        direction: str = "both",
        max_depth: int = 3,
        confidence_threshold: float = 0.0,
    ) -> LineageGraph:
        """
        Build column-level lineage graph.

        Args:
            root_table: Name of the root table
            root_column: Name of the root column
            schema: Optional schema name
            direction: Direction to traverse ('upstream', 'downstream', or 'both')
            max_depth: Maximum depth to traverse
            confidence_threshold: Minimum confidence score for edges (0.0 to 1.0)

        Returns:
            LineageGraph with column nodes and edges

        Example:
            >>> builder = LineageGraphBuilder(engine)
            >>> graph = builder.build_column_graph("orders", "customer_id", direction="upstream")
            >>> print(f"Column lineage: {len(graph.nodes)} columns")
        """
        nodes_dict: Dict[str, LineageNode] = {}
        edges_list: List[LineageEdge] = []
        
        # Create root node
        root_id = self._make_column_id(schema, root_table, root_column)
        nodes_dict[root_id] = LineageNode(
            id=root_id,
            type="column",
            label=f"{root_table}.{root_column}",
            schema=schema,
            table=root_table,
            column=root_column,
            metadata={"is_root": True},
        )
        
        # Get upstream column dependencies
        if direction in ("upstream", "both"):
            upstream_data = self.client.get_upstream_columns(
                root_table, root_column, schema_name=schema, max_depth=max_depth
            )
            self._process_column_lineage_data(
                upstream_data, nodes_dict, edges_list, is_upstream=True
            )
        
        # Get downstream column dependencies
        if direction in ("downstream", "both"):
            downstream_data = self.client.get_downstream_columns(
                root_table, root_column, schema_name=schema, max_depth=max_depth
            )
            self._process_column_lineage_data(
                downstream_data, nodes_dict, edges_list, is_upstream=False
            )
        
        graph = LineageGraph(
            nodes=list(nodes_dict.values()),
            edges=edges_list,
            root_id=root_id,
            direction=direction,
        )
        
        # Filter by confidence if threshold > 0
        if confidence_threshold > 0:
            graph = graph.filter_by_confidence(confidence_threshold)
        
        return graph

    def add_drift_annotations(
        self,
        graph: LineageGraph,
        run_id: Optional[str] = None,
    ) -> LineageGraph:
        """
        Add drift status annotations to graph nodes.

        Queries drift events and marks nodes with drift information.

        Args:
            graph: LineageGraph to annotate
            run_id: Optional run ID to filter drift events

        Returns:
            Annotated LineageGraph

        Example:
            >>> graph = builder.build_table_graph("customers")
            >>> graph = builder.add_drift_annotations(graph)
            >>> drifted_nodes = [n for n in graph.nodes if n.metadata.get("has_drift")]
        """
        # Query drift events from baselinr_events table
        from sqlalchemy import text

        drift_query = """
            SELECT DISTINCT table_name, drift_severity
            FROM baselinr_events
            WHERE event_type = 'DriftDetected'
        """
        
        if run_id:
            drift_query += " AND run_id = :run_id"
        
        drift_query += " ORDER BY timestamp DESC"
        
        with self.engine.connect() as conn:
            if run_id:
                result = conn.execute(text(drift_query), {"run_id": run_id})
            else:
                result = conn.execute(text(drift_query))
            
            drift_data = {}
            for row in result:
                table_name, severity = row
                if table_name not in drift_data:
                    drift_data[table_name] = severity
        
        # Annotate nodes with drift information
        for node in graph.nodes:
            if node.type == "table" and node.table in drift_data:
                node.metadata["has_drift"] = True
                node.metadata["drift_severity"] = drift_data[node.table]
        
        return graph

    def _process_table_lineage_data(
        self,
        lineage_data: List[Dict[str, Any]],
        nodes_dict: Dict[str, LineageNode],
        edges_list: List[LineageEdge],
        is_upstream: bool,
    ) -> None:
        """Process table lineage data and populate nodes/edges."""
        for item in lineage_data:
            schema_name = item.get("schema", "")
            table_name = item.get("table", "")
            depth = item.get("depth", 0)
            lineage_type = item.get("lineage_type", "unknown")
            provider = item.get("provider", "unknown")
            confidence = item.get("confidence_score", 1.0)
            
            # Create node if not exists
            node_id = self._make_table_id(schema_name, table_name)
            if node_id not in nodes_dict:
                nodes_dict[node_id] = LineageNode(
                    id=node_id,
                    type="table",
                    label=table_name,
                    schema=schema_name if schema_name else None,
                    table=table_name,
                    metadata={
                        "depth": depth,
                        "provider": provider,
                        "is_stale": item.get("is_stale", False),
                    },
                )
            
            # Note: Edges are created during recursive traversal
            # We'll need to infer edges from the depth information
            # For now, we skip edge creation as the lineage client doesn't provide parent info

    def _process_column_lineage_data(
        self,
        lineage_data: List[Dict[str, Any]],
        nodes_dict: Dict[str, LineageNode],
        edges_list: List[LineageEdge],
        is_upstream: bool,
    ) -> None:
        """Process column lineage data and populate nodes/edges."""
        for item in lineage_data:
            schema_name = item.get("schema", "")
            table_name = item.get("table", "")
            column_name = item.get("column", "")
            depth = item.get("depth", 0)
            lineage_type = item.get("lineage_type", "unknown")
            provider = item.get("provider", "unknown")
            confidence = item.get("confidence_score", 1.0)
            transformation = item.get("transformation_expression")
            
            # Create node if not exists
            node_id = self._make_column_id(schema_name, table_name, column_name)
            if node_id not in nodes_dict:
                nodes_dict[node_id] = LineageNode(
                    id=node_id,
                    type="column",
                    label=f"{table_name}.{column_name}",
                    schema=schema_name if schema_name else None,
                    table=table_name,
                    column=column_name,
                    metadata={
                        "depth": depth,
                        "provider": provider,
                        "transformation": transformation,
                        "is_stale": item.get("is_stale", False),
                    },
                )

    def _make_table_id(self, schema: Optional[str], table: str) -> str:
        """Generate unique ID for table node."""
        if schema:
            return f"{schema}.{table}"
        return table

    def _make_column_id(self, schema: Optional[str], table: str, column: str) -> str:
        """Generate unique ID for column node."""
        if schema:
            return f"{schema}.{table}.{column}"
        return f"{table}.{column}"
    
    def get_all_tables(self) -> List[Dict[str, str]]:
        """
        Get all tables with lineage data.

        Returns:
            List of table info dictionaries with schema and table names

        Example:
            >>> tables = builder.get_all_tables()
            >>> for table in tables:
            ...     print(f"{table['schema']}.{table['table']}")
        """
        from sqlalchemy import text

        query = text(
            f"""
            SELECT DISTINCT downstream_schema, downstream_table
            FROM {self.lineage_table}
            UNION
            SELECT DISTINCT upstream_schema, upstream_table
            FROM {self.lineage_table}
            ORDER BY downstream_schema, downstream_table
        """
        )
        
        with self.engine.connect() as conn:
            result = conn.execute(query)
            tables = [
                {"schema": row[0] or "", "table": row[1]}
                for row in result
            ]
        
        return tables

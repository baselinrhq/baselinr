"""
Tool definitions and registry for Baselinr chat agent.

Provides the tools that the LLM can call to query data quality information.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Tool that LLM can invoke."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    function: Callable
    category: str = "general"
    examples: List[str] = field(default_factory=list)

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[Tool]:
        """List all tools."""
        return list(self.tools.values())

    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get tools by category."""
        return [t for t in self.tools.values() if t.category == category]

    def to_openai_format(self) -> List[Dict[str, Any]]:
        """Convert all tools to OpenAI format."""
        return [tool.to_openai_format() for tool in self.tools.values()]

    def to_anthropic_format(self) -> List[Dict[str, Any]]:
        """Convert all tools to Anthropic format."""
        return [tool.to_anthropic_format() for tool in self.tools.values()]

    def get_tool_descriptions(self) -> str:
        """Get formatted descriptions of all tools."""
        descriptions = []
        for tool in self.tools.values():
            desc = f"- {tool.name}: {tool.description}"
            descriptions.append(desc)
        return "\n".join(descriptions)


def setup_tools(registry: ToolRegistry, engine: Engine, config: Dict[str, Any]) -> None:
    """
    Setup and register all Baselinr tools.

    Args:
        registry: Tool registry to register tools with
        engine: SQLAlchemy engine for database access
        config: Configuration dictionary
    """
    from baselinr.query.client import MetadataQueryClient

    # Create query client
    query_client = MetadataQueryClient(
        engine=engine,
        runs_table=config.get("runs_table", "baselinr_runs"),
        results_table=config.get("results_table", "baselinr_results"),
        events_table=config.get("events_table", "baselinr_events"),
    )

    # Register all core tools
    _register_query_runs_tool(registry, query_client)
    _register_query_drift_tool(registry, query_client)
    _register_query_anomalies_tool(registry, query_client, engine, config)
    _register_get_table_profile_tool(registry, query_client)
    _register_get_column_history_tool(registry, engine, config)
    _register_compare_runs_tool(registry, query_client)
    _register_search_tables_tool(registry, engine, config)
    _register_get_lineage_tool(registry, query_client)

    logger.info(f"Registered {len(registry.tools)} chat tools")


def _register_query_runs_tool(registry: ToolRegistry, client) -> None:
    """Register the query_recent_runs tool."""

    def query_recent_runs(
        table: Optional[str] = None,
        schema: Optional[str] = None,
        limit: int = 10,
        days: int = 7,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query recent profiling runs."""
        try:
            runs = client.query_runs(
                table=table,
                schema=schema,
                status=status,
                days=days,
                limit=limit,
            )
            return [run.to_dict() for run in runs]
        except Exception as e:
            logger.error(f"Error querying runs: {e}")
            return [{"error": str(e)}]

    registry.register(
        Tool(
            name="query_recent_runs",
            description=(
                "Query recent profiling runs. Use this to see what tables have been "
                "profiled recently, their status, row counts, and when they were last profiled."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Filter by table name (optional)",
                    },
                    "schema": {
                        "type": "string",
                        "description": "Filter by schema name (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of runs to return (default: 10)",
                        "default": 10,
                    },
                    "days": {
                        "type": "integer",
                        "description": "Look back this many days (default: 7)",
                        "default": 7,
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status (e.g., 'completed', 'failed')",
                    },
                },
                "required": [],
            },
            function=query_recent_runs,
            category="profiling",
            examples=[
                "What tables have been profiled recently?",
                "Show me runs for the orders table",
                "List failed profiling runs from the last week",
            ],
        )
    )


def _register_query_drift_tool(registry: ToolRegistry, client) -> None:
    """Register the query_drift_events tool."""

    def query_drift_events(
        table: Optional[str] = None,
        column: Optional[str] = None,
        severity: Optional[str] = None,
        days: int = 7,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Query drift detection events."""
        try:
            events = client.query_drift_events(
                table=table,
                severity=severity,
                days=days,
                limit=limit,
            )

            # Filter by column if specified
            if column:
                events = [e for e in events if e.column_name == column]

            return [event.to_dict() for event in events]
        except Exception as e:
            logger.error(f"Error querying drift events: {e}")
            return [{"error": str(e)}]

    registry.register(
        Tool(
            name="query_drift_events",
            description=(
                "Query drift detection events. Drift indicates significant changes in "
                "data distribution or metrics. Filter by table, column, or severity "
                "(low, medium, high)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Filter by table name",
                    },
                    "column": {
                        "type": "string",
                        "description": "Filter by column name",
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Filter by severity level",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Look back this many days (default: 7)",
                        "default": 7,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum events to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
            function=query_drift_events,
            category="drift",
            examples=[
                "Show me high severity drift events",
                "What drift has occurred in the customers table?",
                "Are there any drift issues with the email column?",
            ],
        )
    )


def _register_query_anomalies_tool(
    registry: ToolRegistry, client, engine: Engine, config: Dict[str, Any]
) -> None:
    """Register the query_anomalies tool."""

    def query_anomalies(
        table: Optional[str] = None,
        column: Optional[str] = None,
        metric: Optional[str] = None,
        days: int = 7,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Query anomaly detection events."""
        try:
            # Query events with anomaly types
            events = client.query_drift_events(
                table=table,
                days=days,
                limit=limit * 2,  # Get more to filter
            )

            # Filter for anomaly-type events
            anomalies = []
            for event in events:
                event_dict = event.to_dict()
                event_type = event_dict.get("event_type", "")

                # Include drift events and anomaly events
                if "anomaly" in event_type.lower() or event_dict.get("drift_severity"):
                    if column and event_dict.get("column_name") != column:
                        continue
                    if metric and event_dict.get("metric_name") != metric:
                        continue
                    anomalies.append(event_dict)

            return anomalies[:limit]
        except Exception as e:
            logger.error(f"Error querying anomalies: {e}")
            return [{"error": str(e)}]

    registry.register(
        Tool(
            name="query_anomalies",
            description=(
                "Query anomaly detection events. Anomalies are statistically unusual values "
                "detected in metrics like null_rate, mean, distinct_count, etc. "
                "Use this to find data quality issues."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Filter by table name",
                    },
                    "column": {
                        "type": "string",
                        "description": "Filter by column name",
                    },
                    "metric": {
                        "type": "string",
                        "description": "Filter by metric (e.g., null_rate, mean, distinct_count)",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Look back this many days (default: 7)",
                        "default": 7,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum anomalies to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
            function=query_anomalies,
            category="anomaly",
            examples=[
                "What anomalies have been detected?",
                "Show me null rate anomalies in the orders table",
                "Are there any issues with the customer_id column?",
            ],
        )
    )


def _register_get_table_profile_tool(registry: ToolRegistry, client) -> None:
    """Register the get_table_profile tool."""

    def get_table_profile(
        table: str,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get detailed profile for a specific table."""
        try:
            # Get run details
            if run_id:
                result = client.query_run_details(run_id, dataset_name=table)
            else:
                # Get latest run for this table
                runs = client.query_runs(table=table, limit=1)
                if not runs:
                    return {"error": f"No profiling runs found for table '{table}'"}
                result = client.query_run_details(runs[0].run_id, dataset_name=table)

            if not result:
                return {"error": f"No profile found for table '{table}'"}

            return dict(result)  # type: ignore[arg-type]
        except Exception as e:
            logger.error(f"Error getting table profile: {e}")
            return {"error": str(e)}

    registry.register(
        Tool(
            name="get_table_profile",
            description=(
                "Get detailed profile for a specific table including all column metrics. "
                "This gives you the full picture of a table's data quality - row counts, "
                "null rates, distinct counts, distributions, and more."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name to get profile for (required)",
                    },
                    "run_id": {
                        "type": "string",
                        "description": "Specific run ID (optional, defaults to latest)",
                    },
                },
                "required": ["table"],
            },
            function=get_table_profile,
            category="profiling",
            examples=[
                "Show me the profile for the customers table",
                "What metrics do we have for orders?",
                "Get detailed info about the products table",
            ],
        )
    )


def _register_get_column_history_tool(
    registry: ToolRegistry, engine: Engine, config: Dict[str, Any]
) -> None:
    """Register the get_column_history tool."""
    from sqlalchemy import text

    results_table = config.get("results_table", "baselinr_results")

    def get_column_history(
        table: str,
        column: str,
        metric: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get historical trend for a specific column metric."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            query = text(
                f"""
                SELECT metric_value, profiled_at, run_id
                FROM {results_table}
                WHERE dataset_name = :table
                AND column_name = :column
                AND metric_name = :metric
                AND profiled_at > :start_date
                ORDER BY profiled_at ASC
            """
            )

            with engine.connect() as conn:
                results = conn.execute(
                    query,
                    {
                        "table": table,
                        "column": column,
                        "metric": metric,
                        "start_date": start_date,
                    },
                ).fetchall()

            history = []
            for row in results:
                try:
                    value = float(row[0]) if row[0] is not None else None
                except (ValueError, TypeError):
                    value = row[0]

                profiled_at = row[1]
                if isinstance(profiled_at, str):
                    profiled_at_str = profiled_at
                elif isinstance(profiled_at, datetime):
                    profiled_at_str = profiled_at.isoformat()
                else:
                    profiled_at_str = str(profiled_at)

                history.append(
                    {
                        "value": value,
                        "profiled_at": profiled_at_str,
                        "run_id": row[2],
                    }
                )

            # Add summary statistics
            numeric_values = [h["value"] for h in history if isinstance(h["value"], (int, float))]
            if numeric_values:
                import statistics

                summary: Dict[str, Any] = {
                    "count": len(numeric_values),
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "mean": statistics.mean(numeric_values),
                }
                if len(numeric_values) > 1:
                    summary["stddev"] = statistics.stdev(numeric_values)
                    # Calculate trend (recent vs historical)
                    mid = len(numeric_values) // 2
                    if mid > 0:
                        recent_avg = statistics.mean(numeric_values[mid:])
                        historical_avg = statistics.mean(numeric_values[:mid])
                        if historical_avg != 0:
                            trend_pct = ((recent_avg - historical_avg) / abs(historical_avg)) * 100
                            summary["trend_percent"] = round(trend_pct, 2)
                            summary["trend"] = (
                                "increasing"
                                if trend_pct > 5
                                else "decreasing" if trend_pct < -5 else "stable"
                            )
                        else:
                            summary["trend"] = "stable"

                return {"history": history, "summary": summary}

            return {"history": history, "summary": {"count": len(history)}}

        except Exception as e:
            logger.error(f"Error getting column history: {e}")
            return {"error": str(e)}

    registry.register(
        Tool(
            name="get_column_history",
            description=(
                "Get historical trend for a specific column metric over time. "
                "This shows how a metric has changed, helping identify patterns, "
                "seasonality, or gradual drift."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name (required)",
                    },
                    "column": {
                        "type": "string",
                        "description": "Column name (required)",
                    },
                    "metric": {
                        "type": "string",
                        "description": "Metric to track (e.g., mean, null_ratio, distinct_count)",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days of history (default: 30)",
                        "default": 30,
                    },
                },
                "required": ["table", "column", "metric"],
            },
            function=get_column_history,
            category="trends",
            examples=[
                "Show me the trend for order_amount mean over the last month",
                "How has the null rate for email changed?",
                "Get the history of distinct_count for customer_id",
            ],
        )
    )


def _register_compare_runs_tool(registry: ToolRegistry, client) -> None:
    """Register the compare_runs tool."""

    def compare_runs(
        table: str,
        run_id_1: Optional[str] = None,
        run_id_2: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare two profiling runs."""
        try:
            # Get runs for the table
            runs = client.query_runs(table=table, limit=10)
            if len(runs) < 2:
                return {"error": f"Not enough runs to compare for table '{table}'"}

            # Default to latest two runs if not specified
            if not run_id_1:
                run_id_1 = runs[0].run_id
            if not run_id_2:
                run_id_2 = runs[1].run_id if len(runs) > 1 else runs[0].run_id

            # Get details for both runs
            run1 = client.query_run_details(run_id_1, dataset_name=table)
            run2 = client.query_run_details(run_id_2, dataset_name=table)

            if not run1 or not run2:
                return {"error": "Could not retrieve run details"}

            # Compare
            comparison: Dict[str, Any] = {
                "run_1": {
                    "run_id": run1["run_id"],
                    "profiled_at": run1.get("profiled_at"),
                    "row_count": run1.get("row_count"),
                    "column_count": run1.get("column_count"),
                },
                "run_2": {
                    "run_id": run2["run_id"],
                    "profiled_at": run2.get("profiled_at"),
                    "row_count": run2.get("row_count"),
                    "column_count": run2.get("column_count"),
                },
                "differences": [],
            }

            # Calculate row count change
            r1_rows = run1.get("row_count") or 0
            r2_rows = run2.get("row_count") or 0
            if r1_rows != r2_rows:
                change = r1_rows - r2_rows
                pct = (change / r2_rows * 100) if r2_rows > 0 else 0
                comparison["row_count_change"] = change
                comparison["row_count_change_percent"] = round(pct, 2)

            # Compare column metrics
            cols1 = {c["column_name"]: c for c in run1.get("columns", [])}
            cols2 = {c["column_name"]: c for c in run2.get("columns", [])}

            for col_name in set(cols1.keys()) | set(cols2.keys()):
                c1 = cols1.get(col_name, {})
                c2 = cols2.get(col_name, {})

                m1 = c1.get("metrics", {})
                m2 = c2.get("metrics", {})

                for metric in set(m1.keys()) | set(m2.keys()):
                    v1 = m1.get(metric)
                    v2 = m2.get(metric)

                    # Only compare numeric metrics
                    try:
                        v1_num = float(v1) if v1 is not None else None
                        v2_num = float(v2) if v2 is not None else None
                    except (ValueError, TypeError):
                        continue

                    if v1_num is not None and v2_num is not None and v1_num != v2_num:
                        diff = v1_num - v2_num
                        pct = (diff / abs(v2_num) * 100) if v2_num != 0 else 0

                        if abs(pct) > 1:  # Only show >1% changes
                            comparison["differences"].append(
                                {
                                    "column": col_name,
                                    "metric": metric,
                                    "run_1_value": v1_num,
                                    "run_2_value": v2_num,
                                    "change": round(diff, 4),
                                    "change_percent": round(pct, 2),
                                }
                            )

            # Sort differences by absolute change percent
            comparison["differences"].sort(
                key=lambda x: abs(x.get("change_percent", 0)), reverse=True
            )

            return comparison

        except Exception as e:
            logger.error(f"Error comparing runs: {e}")
            return {"error": str(e)}

    registry.register(
        Tool(
            name="compare_runs",
            description=(
                "Compare two profiling runs for a table to see what changed. "
                "This helps identify when and how metrics changed between runs."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name (required)",
                    },
                    "run_id_1": {
                        "type": "string",
                        "description": "First run ID (optional, defaults to latest)",
                    },
                    "run_id_2": {
                        "type": "string",
                        "description": "Second run ID (optional, defaults to second latest)",
                    },
                },
                "required": ["table"],
            },
            function=compare_runs,
            category="comparison",
            examples=[
                "Compare the last two runs for orders",
                "What changed between the most recent profiles of customers?",
                "Show me the differences in the products table",
            ],
        )
    )


def _register_search_tables_tool(
    registry: ToolRegistry, engine: Engine, config: Dict[str, Any]
) -> None:
    """Register the search_tables tool."""
    from sqlalchemy import text

    runs_table = config.get("runs_table", "baselinr_runs")

    def search_tables(
        query: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for tables by name."""
        try:
            search_query = text(
                f"""
                SELECT DISTINCT dataset_name, schema_name,
                       MAX(profiled_at) as last_profiled,
                       MAX(row_count) as row_count,
                       MAX(column_count) as column_count
                FROM {runs_table}
                WHERE LOWER(dataset_name) LIKE LOWER(:pattern)
                   OR LOWER(schema_name) LIKE LOWER(:pattern)
                GROUP BY dataset_name, schema_name
                ORDER BY last_profiled DESC
                LIMIT :limit
            """
            )

            pattern = f"%{query}%"

            with engine.connect() as conn:
                results = conn.execute(
                    search_query, {"pattern": pattern, "limit": limit}
                ).fetchall()

            tables = []
            for row in results:
                last_profiled = row[2]
                if isinstance(last_profiled, datetime):
                    last_profiled = last_profiled.isoformat()
                elif last_profiled:
                    last_profiled = str(last_profiled)

                tables.append(
                    {
                        "table_name": row[0],
                        "schema_name": row[1],
                        "last_profiled": last_profiled,
                        "row_count": row[3],
                        "column_count": row[4],
                    }
                )

            return tables

        except Exception as e:
            logger.error(f"Error searching tables: {e}")
            return [{"error": str(e)}]

    registry.register(
        Tool(
            name="search_tables",
            description=(
                "Search for tables by name or schema. Use this when you don't know "
                "the exact table name or want to find related tables."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (matches table name or schema)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
            function=search_tables,
            category="discovery",
            examples=[
                "Find tables with 'order' in the name",
                "Search for customer-related tables",
                "What tables are in the analytics schema?",
            ],
        )
    )


def _register_get_lineage_tool(registry: ToolRegistry, client) -> None:
    """Register the get_lineage tool."""

    def get_lineage(
        table: str,
        schema: Optional[str] = None,
        direction: str = "both",
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """Get lineage information for a table."""
        try:
            result: Dict[str, Any] = {
                "table": table,
                "schema": schema,
                "upstream": [],
                "downstream": [],
            }

            if direction in ("upstream", "both"):
                try:
                    upstream = client.query_lineage_upstream(
                        table_name=table,
                        schema_name=schema,
                        max_depth=max_depth,
                    )
                    result["upstream"] = upstream
                except Exception as e:
                    logger.debug(f"Could not get upstream lineage: {e}")
                    result["upstream_error"] = str(e)

            if direction in ("downstream", "both"):
                try:
                    downstream = client.query_lineage_downstream(
                        table_name=table,
                        schema_name=schema,
                        max_depth=max_depth,
                    )
                    result["downstream"] = downstream
                except Exception as e:
                    logger.debug(f"Could not get downstream lineage: {e}")
                    result["downstream_error"] = str(e)

            return result

        except Exception as e:
            logger.error(f"Error getting lineage: {e}")
            return {"error": str(e)}

    registry.register(
        Tool(
            name="get_lineage",
            description=(
                "Get data lineage (upstream sources and downstream dependents) for a table. "
                "This helps understand data flow and impact of data quality issues."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "Table name (required)",
                    },
                    "schema": {
                        "type": "string",
                        "description": "Schema name (optional)",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["upstream", "downstream", "both"],
                        "description": "Lineage direction (default: both)",
                        "default": "both",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse (default: 2)",
                        "default": 2,
                    },
                },
                "required": ["table"],
            },
            function=get_lineage,
            category="lineage",
            examples=[
                "What are the upstream sources for orders?",
                "Show me downstream tables that depend on customers",
                "Get the lineage for the transactions table",
            ],
        )
    )

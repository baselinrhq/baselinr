"""
Profiling plan builder for Baselinr.

Analyzes configuration and builds an execution plan showing what will be profiled
without actually running the profiling logic.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config.schema import BaselinrConfig, TablePattern
from .incremental import IncrementalPlan, IncrementalPlanner, TableRunDecision

logger = logging.getLogger(__name__)


@dataclass
class TablePlan:
    """Plan for profiling a single table."""

    name: str
    schema: Optional[str] = None
    status: str = "ready"
    partition_config: Optional[Dict[str, Any]] = None
    sampling_config: Optional[Dict[str, Any]] = None
    metrics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        """Get fully qualified table name."""
        if self.schema:
            return f"{self.schema}.{self.name}"
        return self.name


@dataclass
class ProfilingPlan:
    """Complete profiling execution plan."""

    run_id: str
    timestamp: datetime
    environment: str
    tables: List[TablePlan] = field(default_factory=list)
    source_type: str = "postgres"
    source_database: str = ""
    drift_strategy: str = "absolute_threshold"
    total_tables: int = 0
    estimated_metrics: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "environment": self.environment,
            "source": {"type": self.source_type, "database": self.source_database},
            "drift_detection": {"strategy": self.drift_strategy},
            "tables": [
                {
                    "name": table.full_name,
                    "schema": table.schema,
                    "table": table.name,
                    "status": table.status,
                    "partition": table.partition_config,
                    "sampling": table.sampling_config,
                    "metrics": table.metrics,
                    "metadata": table.metadata,
                }
                for table in self.tables
            ],
            "summary": {
                "total_tables": self.total_tables,
                "estimated_metrics": self.estimated_metrics,
            },
        }


class PlanBuilder:
    """Builds profiling execution plans from configuration."""

    def __init__(self, config: BaselinrConfig):
        """
        Initialize plan builder.

        Args:
            config: Baselinr configuration
        """
        self.config = config
        self._incremental_planner: Optional[IncrementalPlanner] = None

    def build_plan(self) -> ProfilingPlan:
        """
        Build profiling execution plan from configuration.

        Returns:
            ProfilingPlan with all tables to be profiled

        Raises:
            ValueError: If configuration is invalid or empty
        """
        logger.info("Building profiling execution plan...")

        # Validate configuration
        if not self.config.profiling.tables:
            raise ValueError(
                "No tables configured for profiling. "
                "Add tables to the 'profiling.tables' section in your config."
            )

        # Create plan
        plan = ProfilingPlan(
            run_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            environment=self.config.environment,
            source_type=self.config.source.type,
            source_database=self.config.source.database,
            drift_strategy=self.config.drift_detection.strategy,
        )

        incremental_plan: Optional[IncrementalPlan] = None
        decision_map: Dict[str, TableRunDecision] = {}
        if self.config.incremental.enabled:
            incremental_plan = self.get_tables_to_run(plan.timestamp)
            decision_map = {
                self._table_key(decision.table): decision for decision in incremental_plan.decisions
            }

        # Build table plans
        for table_pattern in self.config.profiling.tables:
            table_plan = self._build_table_plan(
                table_pattern, decision_map.get(self._table_key(table_pattern))
            )
            plan.tables.append(table_plan)

        # Calculate summary statistics
        plan.total_tables = len(plan.tables)
        plan.estimated_metrics = self._estimate_total_metrics(plan.tables)

        logger.info(
            f"Plan built: {plan.total_tables} tables, " f"~{plan.estimated_metrics} metrics"
        )

        return plan

    def _build_table_plan(
        self, pattern: TablePattern, decision: Optional[TableRunDecision]
    ) -> TablePlan:
        """
        Build plan for a single table pattern.

        Args:
            pattern: Table pattern from configuration

        Returns:
            TablePlan for this table
        """
        # Get metrics to compute
        metrics = self.config.profiling.metrics.copy()

        # Build metadata
        metadata: Dict[str, Any] = {
            "compute_histograms": self.config.profiling.compute_histograms,
            "histogram_bins": self.config.profiling.histogram_bins,
            "max_distinct_values": self.config.profiling.max_distinct_values,
        }

        # Convert partition/sampling configs to dicts
        partition_dict = pattern.partition.model_dump() if pattern.partition else None
        sampling_dict = pattern.sampling.model_dump() if pattern.sampling else None

        status = "ready"
        if decision:
            status = decision.action
            metadata.update(
                {
                    "incremental_reason": decision.reason,
                    "changed_partitions": decision.changed_partitions,
                    "estimated_cost": decision.estimated_cost,
                    "snapshot_id": decision.snapshot_id,
                }
            )

        return TablePlan(
            name=pattern.table,
            schema=pattern.schema_,
            status=status,
            partition_config=partition_dict,
            sampling_config=sampling_dict,
            metrics=metrics,
            metadata=metadata,
        )

    def _estimate_total_metrics(self, tables: List[TablePlan]) -> int:
        """
        Estimate total number of metrics that will be computed.

        This is a rough estimate assuming average column counts.

        Args:
            tables: List of table plans

        Returns:
            Estimated total number of metrics
        """
        # Rough estimate: assume 10 columns per table, each with all configured metrics
        avg_columns_per_table = 10
        metrics_per_column = len(self.config.profiling.metrics)

        return len(tables) * avg_columns_per_table * metrics_per_column

    def validate_plan(self, plan: ProfilingPlan) -> List[str]:
        """
        Validate the profiling plan.

        Args:
            plan: Profiling plan to validate

        Returns:
            List of validation warnings (empty if all valid)
        """
        warnings = []

        # Check for duplicate tables
        table_names = [t.full_name for t in plan.tables]
        duplicates = set([name for name in table_names if table_names.count(name) > 1])
        if duplicates:
            warnings.append(f"Duplicate tables in plan: {', '.join(duplicates)}")

        # Check sampling configuration
        for table in plan.tables:
            if table.sampling_config and table.sampling_config.get("enabled"):
                fraction = table.sampling_config.get("fraction", 0.01)
                if fraction <= 0.0 or fraction > 1.0:
                    warnings.append(
                        f"Invalid sampling fraction for {table.full_name}: {fraction} "
                        "(must be between 0.0 and 1.0)"
                    )

        # Check if any metrics are configured
        if not any(table.metrics for table in plan.tables):
            warnings.append("No metrics configured for profiling")

        return warnings

    def get_tables_to_run(self, current_time: Optional[datetime] = None) -> IncrementalPlan:
        """Expose incremental planner decisions for sensors/CLI."""
        if self._incremental_planner is None:
            self._incremental_planner = IncrementalPlanner(self.config)
        return self._incremental_planner.get_tables_to_run(current_time)

    def _table_key(self, pattern: TablePattern) -> str:
        return f"{pattern.schema_}.{pattern.table}" if pattern.schema_ else pattern.table


def print_plan(plan: ProfilingPlan, format: str = "text", verbose: bool = False):
    """
    Print profiling plan to stdout.

    Args:
        plan: Profiling plan to print
        format: Output format ("text" or "json")
        verbose: Whether to include verbose details
    """
    if format == "json":
        import json

        print(json.dumps(plan.to_dict(), indent=2))
    else:
        _print_text_plan(plan, verbose)


def _print_text_plan(plan: ProfilingPlan, verbose: bool = False):
    """Print plan in human-readable text format with Rich formatting."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        # Import from cli_output if available, otherwise define locally
        try:
            from ..cli_output import get_status_indicator, safe_print
        except ImportError:
            # Define locally if import fails
            def get_status_indicator(state: str) -> Text:
                color_map = {
                    "optimized": "#a78bfa",
                    "profiling": "#4a90e2",
                }
                color = color_map.get(state, "#4a90e2")
                return Text("●", style=f"bold {color}")

            def safe_print(*args, **kwargs) -> None:
                print(*args, **kwargs)

        console = Console()
        use_rich = True
    except (ImportError, AttributeError):
        use_rich = False
        console = None

        def get_status_indicator_dummy(_state: str) -> str:
            return ""

    if not use_rich or not console:
        # Fallback to plain text
        _print_text_plan_plain(plan, verbose)
        return

    # Header Panel
    header_text = "[bold]PROFILING EXECUTION PLAN[/bold]\n\n"
    header_text += f"Run ID: [cyan]{plan.run_id[:8]}...[/cyan]\n"
    header_text += f"Timestamp: [dim]{plan.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}[/dim]\n"
    header_text += f"Environment: [green]{plan.environment}[/green]\n"
    header_text += f"Source: [cyan]{plan.source_type}[/cyan] ([dim]{plan.source_database}[/dim])\n"
    header_text += f"Drift Strategy: [yellow]{plan.drift_strategy}[/yellow]"
    header_panel = Panel(header_text, border_style="#4a90e2", title="[bold]Plan[/bold]")
    console.print()
    console.print(header_panel)

    # Tables Table
    tables_table = Table(
        title=f"Tables to be Profiled ({plan.total_tables})",
        show_header=True,
        header_style="bold magenta",
    )
    tables_table.add_column("#", justify="right", style="dim")
    tables_table.add_column("Table", style="cyan")
    tables_table.add_column("Status", justify="center")
    tables_table.add_column("Partition", style="dim")
    tables_table.add_column("Sampling", style="dim")
    tables_table.add_column("Optimized", justify="center")

    for i, table in enumerate(plan.tables, 1):
        # Determine if optimized (sampling or partial partition)
        is_optimized = False
        optimized_indicator = ""
        if table.sampling_config and table.sampling_config.get("enabled"):
            is_optimized = True
            optimized_indicator = get_status_indicator("optimized")
        elif table.partition_config and table.partition_config.get("strategy") != "all":
            is_optimized = True
            optimized_indicator = get_status_indicator("optimized")

        # Format partition info
        partition_str = "full table"
        if table.partition_config:
            partition = table.partition_config
            strategy = partition.get("strategy", "all")
            if strategy != "all":
                partition_str = f"{strategy}"
                if partition.get("key"):
                    partition_str += f" on {partition['key']}"
                if partition.get("strategy") == "recent_n" and partition.get("recent_n"):
                    partition_str += f" (N={partition['recent_n']})"

        # Format sampling info
        sampling_str = "none"
        if table.sampling_config and table.sampling_config.get("enabled"):
            sampling = table.sampling_config
            fraction = sampling.get("fraction", 0.01) * 100
            method = sampling.get("method", "random")
            sampling_str = f"{method} ({fraction:.2f}%)"
            if sampling.get("max_rows"):
                sampling_str += f", max {sampling['max_rows']:,} rows"

        tables_table.add_row(
            str(i),
            table.full_name,
            table.status,
            partition_str,
            sampling_str,
            str(optimized_indicator) if is_optimized else "",
        )

    console.print()
    console.print(tables_table)

    # Summary Table
    summary_table = Table(title="Summary", show_header=True, header_style="bold green")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", justify="right", style="green")
    summary_table.add_row("Total Tables", str(plan.total_tables))
    summary_table.add_row("Estimated Metrics", f"~{plan.estimated_metrics}")

    if verbose:
        compute_hist = (
            plan.tables[0].metadata.get("compute_histograms", False) if plan.tables else "N/A"
        )
        hist_bins = plan.tables[0].metadata.get("histogram_bins", "N/A") if plan.tables else "N/A"
        max_dist = (
            plan.tables[0].metadata.get("max_distinct_values", "N/A") if plan.tables else "N/A"
        )
        summary_table.add_row("Compute Histograms", str(compute_hist))
        summary_table.add_row("Histogram Bins", str(hist_bins))
        summary_table.add_row("Max Distinct Values", str(max_dist))

    console.print()
    console.print(summary_table)

    # Configuration Details section (verbose only)
    if verbose:
        console.print()
        # Print title explicitly so it appears in captured output
        console.print("[bold yellow]Configuration Details[/bold yellow]")
        config_table = Table(
            show_header=True,
            header_style="bold yellow",
        )
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", justify="right", style="green")

        compute_hist = (
            plan.tables[0].metadata.get("compute_histograms", False) if plan.tables else "N/A"
        )
        hist_bins = plan.tables[0].metadata.get("histogram_bins", "N/A") if plan.tables else "N/A"
        max_dist = (
            plan.tables[0].metadata.get("max_distinct_values", "N/A") if plan.tables else "N/A"
        )

        config_table.add_row("Compute Histograms", str(compute_hist))
        config_table.add_row("Histogram Bins", str(hist_bins))
        config_table.add_row("Max Distinct Values", str(max_dist))

        console.print(config_table)


def _print_text_plan_plain(plan: ProfilingPlan, verbose: bool = False):
    """Print plan in plain text format (fallback)."""
    print("\n" + "=" * 70)
    print("PROFILING EXECUTION PLAN")
    print("=" * 70)

    # Header information
    print(f"\nRun ID: {plan.run_id}")
    print(f"Timestamp: {plan.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Environment: {plan.environment}")
    print(f"Source: {plan.source_type} ({plan.source_database})")
    print(f"Drift Strategy: {plan.drift_strategy}")

    # Tables section
    print(f"\n{'-' * 70}")
    print(f"TABLES TO BE PROFILED ({plan.total_tables})")
    print("-" * 70)

    for i, table in enumerate(plan.tables, 1):
        print(f"\n{i}. {table.full_name}")
        print(f"   Status: {table.status}")

        # Show partition configuration
        if table.partition_config:
            partition = table.partition_config
            print(f"   Partition: {partition.get('strategy', 'all')}", end="")
            if partition.get("key"):
                print(f" on {partition['key']}", end="")
            if partition.get("strategy") == "recent_n" and partition.get("recent_n"):
                print(f" (N={partition['recent_n']})", end="")
            print()
        else:
            print("   Partition: full table")

        # Show sampling configuration
        if table.sampling_config and table.sampling_config.get("enabled"):
            sampling = table.sampling_config
            fraction = sampling.get("fraction", 0.01) * 100
            method = sampling.get("method", "random")
            print(f"   Sampling: {method} ({fraction:.2f}%)", end="")
            if sampling.get("max_rows"):
                print(f", max {sampling['max_rows']:,} rows", end="")
            print()
        else:
            print("   Sampling: none (full dataset)")

        if verbose:
            print(f"   Metrics ({len(table.metrics)}): {', '.join(table.metrics)}")
            if table.metadata:
                print("   Configuration:")
                for key, value in table.metadata.items():
                    print(f"     - {key}: {value}")

    # Summary
    print(f"\n{'-' * 70}")
    print("SUMMARY")
    print("-" * 70)
    print(f"Total Tables: {plan.total_tables}")
    print(f"Estimated Metrics: ~{plan.estimated_metrics}")

    if verbose:
        print("\nConfiguration Details:")
        compute_hist = (
            plan.tables[0].metadata.get("compute_histograms", False) if plan.tables else "N/A"
        )
        print(f"  - Compute Histograms: {compute_hist}")
        hist_bins = plan.tables[0].metadata.get("histogram_bins", "N/A") if plan.tables else "N/A"
        print(f"  - Histogram Bins: {hist_bins}")
        max_dist = (
            plan.tables[0].metadata.get("max_distinct_values", "N/A") if plan.tables else "N/A"
        )
        print(f"  - Max Distinct Values: {max_dist}")

    print("\n" + "=" * 70)
    print(f"Plan built successfully. Ready to profile {plan.total_tables} table(s).")
    print("=" * 70 + "\n")

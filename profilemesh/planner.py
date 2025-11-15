"""
Profiling plan builder for ProfileMesh.

Analyzes configuration and builds an execution plan showing what will be profiled
without actually running the profiling logic.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import logging

from .config.schema import ProfileMeshConfig, TablePattern
from .incremental import IncrementalPlanner, IncrementalPlan, TableRunDecision

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
            "source": {
                "type": self.source_type,
                "database": self.source_database
            },
            "drift_detection": {
                "strategy": self.drift_strategy
            },
            "tables": [
                {
                    "name": table.full_name,
                    "schema": table.schema,
                    "table": table.name,
                    "status": table.status,
                    "partition": table.partition_config,
                    "sampling": table.sampling_config,
                    "metrics": table.metrics,
                    "metadata": table.metadata
                }
                for table in self.tables
            ],
            "summary": {
                "total_tables": self.total_tables,
                "estimated_metrics": self.estimated_metrics
            }
        }


class PlanBuilder:
    """Builds profiling execution plans from configuration."""
    
    def __init__(self, config: ProfileMeshConfig):
        """
        Initialize plan builder.
        
        Args:
            config: ProfileMesh configuration
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
            drift_strategy=self.config.drift_detection.strategy
        )
        
        incremental_plan: Optional[IncrementalPlan] = None
        decision_map: Dict[str, TableRunDecision] = {}
        if self.config.incremental.enabled:
            incremental_plan = self.get_tables_to_run(plan.timestamp)
            decision_map = {
                self._table_key(decision.table): decision
                for decision in incremental_plan.decisions
            }
        
        # Build table plans
        for table_pattern in self.config.profiling.tables:
            table_plan = self._build_table_plan(table_pattern, decision_map.get(self._table_key(table_pattern)))
            plan.tables.append(table_plan)
        
        # Calculate summary statistics
        plan.total_tables = len(plan.tables)
        plan.estimated_metrics = self._estimate_total_metrics(plan.tables)
        
        logger.info(f"Plan built: {plan.total_tables} tables, "
                   f"~{plan.estimated_metrics} metrics")
        
        return plan
    
    def _build_table_plan(self, pattern: TablePattern, decision: Optional[TableRunDecision]) -> TablePlan:
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
        metadata = {
            "compute_histograms": self.config.profiling.compute_histograms,
            "histogram_bins": self.config.profiling.histogram_bins,
            "max_distinct_values": self.config.profiling.max_distinct_values
        }
        
        # Convert partition/sampling configs to dicts
        partition_dict = pattern.partition.model_dump() if pattern.partition else None
        sampling_dict = pattern.sampling.model_dump() if pattern.sampling else None
        
        status = "ready"
        if decision:
            status = decision.action
            metadata.update({
                "incremental_reason": decision.reason,
                "changed_partitions": decision.changed_partitions,
                "estimated_cost": decision.estimated_cost,
                "snapshot_id": decision.snapshot_id,
            })
        
        return TablePlan(
            name=pattern.table,
            schema=pattern.schema_,
            status=status,
            partition_config=partition_dict,
            sampling_config=sampling_dict,
            metrics=metrics,
            metadata=metadata
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
            if table.sampling_config and table.sampling_config.get('enabled'):
                fraction = table.sampling_config.get('fraction', 0.01)
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
    """Print plan in human-readable text format."""
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
            if partition.get('key'):
                print(f" on {partition['key']}", end="")
            if partition.get('strategy') == 'recent_n' and partition.get('recent_n'):
                print(f" (N={partition['recent_n']})", end="")
            print()
        else:
            print(f"   Partition: full table")
        
        # Show sampling configuration
        if table.sampling_config and table.sampling_config.get('enabled'):
            sampling = table.sampling_config
            fraction = sampling.get('fraction', 0.01) * 100
            method = sampling.get('method', 'random')
            print(f"   Sampling: {method} ({fraction:.2f}%)", end="")
            if sampling.get('max_rows'):
                print(f", max {sampling['max_rows']:,} rows", end="")
            print()
        else:
            print(f"   Sampling: none (full dataset)")
        
        if verbose:
            print(f"   Metrics ({len(table.metrics)}): {', '.join(table.metrics)}")
            if table.metadata:
                print(f"   Configuration:")
                for key, value in table.metadata.items():
                    print(f"     - {key}: {value}")
    
    # Summary
    print(f"\n{'-' * 70}")
    print("SUMMARY")
    print("-" * 70)
    print(f"Total Tables: {plan.total_tables}")
    print(f"Estimated Metrics: ~{plan.estimated_metrics}")
    
    if verbose:
        print(f"\nConfiguration Details:")
        print(f"  - Compute Histograms: {plan.tables[0].metadata.get('compute_histograms', False) if plan.tables else 'N/A'}")
        print(f"  - Histogram Bins: {plan.tables[0].metadata.get('histogram_bins', 'N/A') if plan.tables else 'N/A'}")
        print(f"  - Max Distinct Values: {plan.tables[0].metadata.get('max_distinct_values', 'N/A') if plan.tables else 'N/A'}")
    
    print("\n" + "=" * 70)
    print(f"Plan built successfully. Ready to profile {plan.total_tables} table(s).")
    print("=" * 70 + "\n")


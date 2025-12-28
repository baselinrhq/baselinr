"""
Dagster asset factory + job helpers for Baselinr.

This module builds Dagster assets from a Baselinr configuration so that
profiling plans can run as first-class Dagster assets.
"""

import logging
from functools import cached_property
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    from dagster import (
        AssetExecutionContext,
        AssetKey,
        AssetMaterialization,
        AssetSelection,
        ConfigurableResource,
        MetadataValue,
        Output,
        asset,
        define_asset_job,
    )

    DAGSTER_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when Dagster missing
    DAGSTER_AVAILABLE = False
    # Type stub for when Dagster is not available
    MetadataValue = Any  # type: ignore

from ...config.loader import ConfigLoader
from ...config.schema import BaselinrConfig, TablePattern
from ...planner import PlanBuilder, ProfilingPlan, TablePlan
from ...profiling.core import ProfileEngine
from ...storage.writer import ResultWriter
from .events import emit_profiling_event

logger = logging.getLogger(__name__)


def _safe_asset_name(name: str) -> str:
    """Convert dataset/table names into Dagster-friendly asset names."""
    return name.replace(".", "_").replace("-", "_")


def _pattern_identifier(pattern: TablePattern) -> str:
    """Return a fully qualified table identifier for lookups."""
    assert pattern.table is not None, "Table name must be set"
    if pattern.schema_:
        return f"{pattern.schema_}.{pattern.table}"
    return pattern.table


def _plan_lookup(plan: ProfilingPlan) -> Dict[str, TablePlan]:
    """Map table full names to TablePlan entries."""
    lookup: Dict[str, TablePlan] = {}
    for table in plan.tables:
        lookup[table.full_name] = table
    return lookup


def _metadata_value(value: Any) -> Any:  # Returns MetadataValue when Dagster available
    """Coerce arbitrary python objects into Dagster MetadataValue instances."""
    if not DAGSTER_AVAILABLE:
        return value  # Return as-is if Dagster not available

    if isinstance(value, MetadataValue):
        return value
    if isinstance(value, bool):
        return MetadataValue.bool(value)
    if isinstance(value, int):
        return MetadataValue.int(value)
    if isinstance(value, float):
        return MetadataValue.float(value)
    if isinstance(value, (list, dict)):
        return MetadataValue.json(value)
    return MetadataValue.text(str(value))


def _table_metadata_entries(
    table_plan: Optional[TablePlan],
    plan: ProfilingPlan,
) -> Dict[str, Any]:  # Returns Dict[str, MetadataValue] when Dagster available
    """Build metadata entries describing the requested profiling plan."""
    if not table_plan:
        return {
            "drift_strategy": MetadataValue.text(plan.drift_strategy),
        }

    return {
        "schema": MetadataValue.text(table_plan.schema or ""),
        "requested_metrics": MetadataValue.json(table_plan.metrics),
        "sampling": MetadataValue.json(table_plan.sampling_config or {}),
        "partitioning": MetadataValue.json(table_plan.partition_config or {}),
        "drift_strategy": MetadataValue.text(plan.drift_strategy),
    }


def _result_metadata_entries(
    result: Any,
) -> Dict[str, Any]:  # Returns Dict[str, MetadataValue] when Dagster available
    """Convert profiling results into Dagster metadata entries."""
    row_count = result.metadata.get("row_count")
    metadata = {
        "run_id": MetadataValue.text(result.run_id),
        "dataset_name": MetadataValue.text(result.dataset_name),
        "columns_profiled": MetadataValue.int(len(result.columns)),
        "profiled_at": MetadataValue.text(result.profiled_at.isoformat()),
    }
    if row_count is not None:
        metadata["row_count"] = MetadataValue.int(int(row_count))
    return metadata


if DAGSTER_AVAILABLE:

    class BaselinrResource(ConfigurableResource):
        """Dagster resource that caches the Baselinr configuration."""

        config_path: str

        @cached_property
        def config(self) -> BaselinrConfig:
            """Load the configuration once per process."""
            return ConfigLoader.load_from_file(self.config_path)

        def get_config(self) -> BaselinrConfig:
            """Return the cached Baselinr config."""
            return self.config

    def create_profiling_assets(
        config_path: str,
        *,
        asset_name_prefix: str = "baselinr",
        group_name: str = "baselinr_profiling",
        default_tags: Optional[Mapping[str, str]] = None,
        default_metadata: Optional[Mapping[str, Any]] = None,
    ) -> List[Any]:
        """
        Create Dagster assets that materialize Baselinr profiling runs.

        Args:
            config_path: Path to the Baselinr configuration file.
            asset_name_prefix: String prepended to each asset name.
            group_name: Dagster asset group.
            default_tags: Optional tags applied to every asset definition.
            default_metadata: Metadata merged into each asset Output.
        """
        config = ConfigLoader.load_from_file(config_path)
        plan_builder = PlanBuilder(config, config_file_path=config_path)
        # Expand patterns to get concrete table patterns (handles select_schema, patterns, etc.)
        expanded_patterns = plan_builder.expand_table_patterns()

        base_tags = {"baselinr/environment": config.environment}
        if default_tags:
            base_tags.update(default_tags)

        assets: List[Any] = []
        if not expanded_patterns:
            logger.warning(
                "No tables found after expanding patterns. "
                "This may indicate that pattern-based selection found no matches."
            )
        else:
            plan = plan_builder.build_plan()
            plan_index = _plan_lookup(plan)

            for table_pattern in expanded_patterns:
                # Skip patterns without table names (should not happen after expansion, but be safe)
                if table_pattern.table is None:
                    logger.warning(
                        f"Skipping pattern without table name: {table_pattern}. "
                        "This should not happen after expansion."
                    )
                    continue
                table_identifier = _pattern_identifier(table_pattern)
                table_plan = plan_index.get(table_identifier)
                asset_def = _create_table_asset(
                    config_path=config_path,
                    table_pattern=table_pattern,
                    table_plan=table_plan,
                    plan=plan,
                    asset_name_prefix=asset_name_prefix,
                    group_name=group_name,
                    tags=base_tags,
                    default_metadata=default_metadata,
                )
                assets.append(asset_def)

        # Build plan for summary asset (even if no tables found)
        plan = plan_builder.build_plan()

        summary_asset = _create_summary_asset(
            plan=plan,
            asset_name_prefix=asset_name_prefix,
            group_name=group_name,
            tags=base_tags,
            default_metadata=default_metadata,
        )
        assets.append(summary_asset)

        logger.info("Created %s Dagster assets for Baselinr", len(assets))
        return assets

    def _create_table_asset(
        *,
        config_path: str,
        table_pattern: TablePattern,
        table_plan: Optional[TablePlan],
        plan: ProfilingPlan,
        asset_name_prefix: str,
        group_name: str,
        tags: Mapping[str, str],
        default_metadata: Optional[Mapping[str, Any]],
    ):
        """Create an asset definition that profiles a single table."""

        assert table_pattern.table is not None, "Table name must be set"
        table_name = _safe_asset_name(table_pattern.table)
        asset_name = f"{asset_name_prefix}_{table_name}"

        @asset(  # type: ignore[call-overload]
            name=asset_name,
            group_name=group_name,
            description=f"Baselinr profiling for {table_pattern.table}",
            required_resource_keys={"baselinr"},
            tags=dict(tags),
        )
        def table_profiling_asset(context: AssetExecutionContext):
            """Materialize profiling results for one table."""

            resource: BaselinrResource = context.resources.baselinr
            config = resource.get_config()

            assert table_pattern.table is not None, "Table name must be set"
            emit_profiling_event(
                context,
                "profiling_started",
                dataset_name=table_pattern.table,
                environment=config.environment,
            )

            engine = ProfileEngine(config)
            results = engine.profile(table_patterns=[table_pattern])
            if not results:
                raise ValueError(f"No profiling results returned for {table_pattern.table}")

            result = results[0]
            # Create event bus for schema change detection
            from ...cli import create_event_bus

            event_bus = create_event_bus(config)

            writer = ResultWriter(config.storage, baselinr_config=config, event_bus=event_bus)
            try:
                writer.write_results(
                    [result],
                    environment=config.environment,
                    enable_enrichment=config.profiling.enable_enrichment,
                )
            finally:
                writer.close()

            plan_metadata = _table_metadata_entries(table_plan, plan)
            runtime_metadata = _result_metadata_entries(result)
            merged_metadata: Dict[str, Any] = {
                **plan_metadata,
                **runtime_metadata,
            }  # Dict[str, MetadataValue] when Dagster available
            if default_metadata:
                merged_metadata.update({k: _metadata_value(v) for k, v in default_metadata.items()})

            success_mat = AssetMaterialization(
                asset_key=context.asset_key or AssetKey(asset_name),
                metadata={**merged_metadata, "status": MetadataValue.text("completed")},
                description=f"Baselinr run completed for {table_pattern.table}",
            )

            assert table_pattern.table is not None, "Table name must be set"
            emit_profiling_event(
                context,
                "profiling_completed",
                dataset_name=table_pattern.table,
                environment=config.environment,
                run_id=result.run_id,
                column_count=len(result.columns),
                row_count=result.metadata.get("row_count"),
            )

            yield success_mat
            yield Output(
                value={
                    "run_id": result.run_id,
                    "dataset_name": result.dataset_name,
                    "table": table_pattern.table,
                    "schema": table_pattern.schema_,
                    "columns_profiled": len(result.columns),
                },
                metadata=merged_metadata,
            )

        return table_profiling_asset

    def _create_summary_asset(
        *,
        plan: ProfilingPlan,
        asset_name_prefix: str,
        group_name: str,
        tags: Mapping[str, str],
        default_metadata: Optional[Mapping[str, Any]],
    ):
        """Create a summary asset that aggregates the profiling plan."""

        @asset(  # type: ignore[call-overload]
            name=f"{asset_name_prefix}_summary",
            group_name=group_name,
            description="Summary of Baselinr profiling runs",
            required_resource_keys={"baselinr"},
            tags=dict(tags),
        )
        def profiling_summary_asset(context: AssetExecutionContext):
            resource: BaselinrResource = context.resources.baselinr
            config = resource.get_config()

            summary = {
                "environment": config.environment,
                "tables_profiled": plan.total_tables,
                "estimated_metrics": plan.estimated_metrics,
                "tables": [table.full_name for table in plan.tables],
            }

            metadata: Dict[str, Any] = {  # Dict[str, MetadataValue] when Dagster available
                "environment": MetadataValue.text(config.environment),
                "tables_profiled": MetadataValue.int(plan.total_tables),
                "estimated_metrics": MetadataValue.int(plan.estimated_metrics),
                "table_list": MetadataValue.md(
                    "\n".join([f"- {table.full_name}" for table in plan.tables]) or "- none -"
                ),
            }

            if default_metadata:
                metadata.update({k: _metadata_value(v) for k, v in default_metadata.items()})

            yield Output(value=summary, metadata=metadata)

        return profiling_summary_asset

    def create_profiling_job(
        *,
        assets: Sequence[Any],
        job_name: str = "baselinr_profile_all",
        description: str = "Run all Baselinr profiling assets",
    ):
        """
        Create a Dagster job that targets all Baselinr assets.
        """
        asset_keys: List[AssetKey] = []
        for asset_def in assets:
            asset_keys.extend(asset_def.keys)

        if not asset_keys:
            raise ValueError("No assets provided when building the Baselinr job.")

        selection = AssetSelection.assets(*asset_keys)  # type: ignore[arg-type]
        return define_asset_job(
            name=job_name,
            description=description,
            selection=selection,
        )

else:  # pragma: no cover - exercised when Dagster missing

    class BaselinrResource:  # type: ignore[no-redef]
        """Stub resource exposed when Dagster is unavailable."""

        def __init__(self, config_path: str, *args: Any, **kwargs: Any):
            raise ImportError(
                "Dagster is not installed. Install with `pip install baselinr[dagster]`."
            )

    def create_profiling_assets(
        config_path: str,
        *,
        asset_name_prefix: str = "baselinr",
        group_name: str = "baselinr_profiling",
        default_tags: Optional[Mapping[str, str]] = None,
        default_metadata: Optional[Mapping[str, Any]] = None,
    ) -> List[Any]:
        raise ImportError("Dagster is not installed. Install with `pip install baselinr[dagster]`.")

    def create_profiling_job(
        *,
        assets: Sequence[Any],
        job_name: str = "baselinr_profile_all",
        description: str = "Run all Baselinr profiling assets",
    ) -> Any:  # type: ignore[return-value]
        raise ImportError("Dagster is not installed. Install with `pip install baselinr[dagster]`.")


__all__ = [
    "BaselinrResource",
    "create_profiling_assets",
    "create_profiling_job",
]

"""
High-level Python SDK client for Baselinr.

Provides a simple, unified interface for all major Baselinr functionality
including profiling, drift detection, querying, and migrations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from .config.loader import ConfigLoader
from .config.schema import BaselinrConfig, TablePattern

if TYPE_CHECKING:
    from .contracts import (
        DatasetMetadata,
        ODCSAdapter,
        ODCSContract,
        ProfilingTarget,
        ValidationRule,
    )
    from .drift.detector import DriftReport
    from .planner import ProfilingPlan
    from .profiling.core import ProfilingResult
    from .query.client import MetadataQueryClient, RunSummary
    from .storage.migrations.manager import MigrationManager

logger = logging.getLogger(__name__)


class BaselinrClient:
    """
    High-level Python SDK client for Baselinr.

    Provides a unified interface for profiling, drift detection, querying,
    and schema migrations. Handles configuration loading, connection management,
    and event bus setup automatically.

    Example:
        >>> from baselinr import BaselinrClient
        >>> client = BaselinrClient(config_path="config.yml")
        >>> plan = client.plan()
        >>> results = client.profile()
        >>> drift_report = client.detect_drift("customers")
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        config: Optional[Union[BaselinrConfig, Dict[str, Any]]] = None,
    ):
        """
        Initialize Baselinr client.

        Args:
            config_path: Path to configuration file (YAML or JSON)
            config: BaselinrConfig object or configuration dictionary

        Raises:
            ValueError: If neither or both config_path and config are provided
            FileNotFoundError: If config_path doesn't exist
        """
        if config_path and config:
            raise ValueError("Provide either config_path or config, not both")
        if not config_path and not config:
            raise ValueError("Provide either config_path or config")

        # Cache config similar to BaselinrResource in Dagster integration
        self._config_path = config_path
        if config_path:
            self._config = ConfigLoader.load_from_file(config_path)
        else:
            if isinstance(config, dict):
                self._config = ConfigLoader.load_from_dict(config)
            elif isinstance(config, BaselinrConfig):
                self._config = config
            else:
                raise ValueError("config must be BaselinrConfig or dict")

        # Lazy-loaded connections and resources
        self._query_client: Optional["MetadataQueryClient"] = None
        self._event_bus = None
        self._migration_manager: Optional["MigrationManager"] = None

        # Contracts cache
        self._contracts: Optional[List["ODCSContract"]] = None
        self._adapter: Optional["ODCSAdapter"] = None

    @property
    def config(self) -> BaselinrConfig:
        """
        Get cached configuration.

        Returns:
            BaselinrConfig instance
        """
        return self._config

    @property
    def contracts(self) -> List["ODCSContract"]:
        """
        Get loaded ODCS contracts.

        Contracts are loaded from the directory specified in config.contracts.

        Returns:
            List of ODCSContract objects

        Example:
            >>> contracts = client.contracts
            >>> print(f"Loaded {len(contracts)} contracts")
        """
        if self._contracts is None:
            self._contracts = self._load_contracts()
        return self._contracts

    def _load_contracts(self) -> List["ODCSContract"]:
        """Load contracts from configured directory."""
        from .contracts import ContractLoader

        if not self._config.contracts:
            return []

        # Try to get from cache first
        if self._config_path:
            cached = ConfigLoader.get_cached_contracts(self._config_path)
            if cached:
                return cached

        # Load from directory
        contracts_dir = self._config.contracts.directory
        if self._config_path:
            from pathlib import Path

            base_path = Path(self._config_path).parent
            contracts_dir = str(base_path / contracts_dir)

        loader = ContractLoader(
            validate_on_load=self._config.contracts.validate_on_load,
            file_patterns=self._config.contracts.file_patterns,
        )

        try:
            return loader.load_from_directory(
                contracts_dir,
                recursive=self._config.contracts.recursive,
                exclude_patterns=self._config.contracts.exclude_patterns,
            )
        except Exception as e:
            logger.warning(f"Failed to load contracts: {e}")
            return []

    def get_contract(self, name: str) -> Optional["ODCSContract"]:
        """
        Get a specific contract by dataset name or contract ID.

        Args:
            name: Dataset name or contract ID

        Returns:
            ODCSContract if found, None otherwise

        Example:
            >>> contract = client.get_contract("customers")
            >>> if contract:
            ...     print(f"Contract: {contract.info.title}")
        """
        for contract in self.contracts:
            # Match by contract ID
            if contract.id == name:
                return contract
            # Match by dataset name
            if contract.dataset:
                for ds in contract.dataset:
                    if ds.name == name or ds.physicalName == name:
                        return contract
        return None

    def get_contract_datasets(self) -> List[str]:
        """
        Get list of all dataset names from loaded contracts.

        Returns:
            List of dataset names

        Example:
            >>> datasets = client.get_contract_datasets()
            >>> print(f"Found {len(datasets)} datasets in contracts")
        """
        datasets: List[str] = []
        for contract in self.contracts:
            datasets.extend(contract.get_dataset_names())
        return datasets

    def get_profiling_targets_from_contracts(self) -> List["ProfilingTarget"]:
        """
        Convert loaded contracts to profiling targets.

        Returns:
            List of ProfilingTarget objects ready for profiling

        Example:
            >>> targets = client.get_profiling_targets_from_contracts()
            >>> for target in targets:
            ...     print(f"Target: {target.get_full_name()}")
        """
        from .contracts import ODCSAdapter

        if self._adapter is None:
            self._adapter = ODCSAdapter()

        targets: List["ProfilingTarget"] = []
        for contract in self.contracts:
            targets.extend(self._adapter.to_profiling_targets(contract))
        return targets

    def get_validation_rules_from_contracts(self) -> List["ValidationRule"]:
        """
        Convert loaded contracts to validation rules.

        Returns:
            List of ValidationRule objects

        Example:
            >>> rules = client.get_validation_rules_from_contracts()
            >>> print(f"Found {len(rules)} validation rules")
        """
        from .contracts import ODCSAdapter

        if self._adapter is None:
            self._adapter = ODCSAdapter()

        rules: List["ValidationRule"] = []
        for contract in self.contracts:
            rules.extend(self._adapter.to_validation_rules(contract))
        return rules

    def get_dataset_metadata_from_contracts(self) -> List["DatasetMetadata"]:
        """
        Extract dataset metadata from loaded contracts.

        Returns:
            List of DatasetMetadata objects

        Example:
            >>> metadata = client.get_dataset_metadata_from_contracts()
            >>> for ds in metadata:
            ...     print(f"{ds.name}: {len(ds.columns)} columns")
        """
        from .contracts import ODCSAdapter

        if self._adapter is None:
            self._adapter = ODCSAdapter()

        metadata: List["DatasetMetadata"] = []
        for contract in self.contracts:
            metadata.extend(self._adapter.to_dataset_metadata(contract))
        return metadata

    def validate_contracts(self, strict: bool = False) -> Dict[str, Any]:
        """
        Validate all loaded contracts.

        Args:
            strict: If True, treat warnings as errors

        Returns:
            Dictionary with validation results

        Example:
            >>> result = client.validate_contracts()
            >>> if result['valid']:
            ...     print("All contracts are valid")
        """
        from .contracts import ODCSValidator

        validator = ODCSValidator(strict=strict)
        results: Dict[str, Any] = {
            "valid": True,
            "contracts_checked": 0,
            "errors": [],
            "warnings": [],
        }

        for contract in self.contracts:
            results["contracts_checked"] += 1
            result = validator.validate_full(contract)

            if not result.valid:
                results["valid"] = False

            contract_name = contract.id or (
                contract.dataset[0].name if contract.dataset else "unnamed"
            )

            for error in result.errors:
                results["errors"].append(
                    {
                        "contract": contract_name,
                        "message": str(error),
                    }
                )

            for warning in result.warnings:
                results["warnings"].append(
                    {
                        "contract": contract_name,
                        "message": str(warning),
                    }
                )

        return results

    def reload_contracts(self) -> int:
        """
        Reload contracts from the configured directory.

        Returns:
            Number of contracts loaded

        Example:
            >>> count = client.reload_contracts()
            >>> print(f"Reloaded {count} contracts")
        """
        self._contracts = None
        return len(self.contracts)

    def _ensure_query_client(self) -> "MetadataQueryClient":
        """Lazy initialize query client for query methods."""
        if self._query_client is None:
            from .connectors.factory import create_connector
            from .query.client import MetadataQueryClient

            connector = create_connector(self.config.storage.connection, self.config.retry)
            self._query_client = MetadataQueryClient(
                connector.engine,
                runs_table=self.config.storage.runs_table,
                results_table=self.config.storage.results_table,
                events_table="baselinr_events",  # Default events table name
            )
        return self._query_client

    def _get_event_bus(self):
        """Get or create event bus from config."""
        if self._event_bus is None:
            from .cli import create_event_bus

            self._event_bus = create_event_bus(self.config)
        return self._event_bus

    def plan(
        self, table_patterns: Optional[List[TablePattern]] = None, verbose: bool = False
    ) -> "ProfilingPlan":
        """
        Build execution plan without running profiling.

        Args:
            table_patterns: Optional list of table patterns to plan for
                          (uses config if not provided). Patterns will be expanded.
            verbose: Whether to include verbose details in plan

        Returns:
            ProfilingPlan object with execution details

        Example:
            >>> plan = client.plan()
            >>> print(f"Will profile {plan.total_tables} tables")
        """
        from .planner import PlanBuilder

        builder = PlanBuilder(self._config, config_file_path=self._config_path)

        if table_patterns:
            # Expand custom patterns first
            expanded_patterns = builder.expand_table_patterns(table_patterns)
            # Build plan with expanded patterns
            # Create a temporary config copy with expanded patterns
            from copy import deepcopy

            temp_config = deepcopy(self._config)
            temp_config.profiling.tables = expanded_patterns
            temp_builder = PlanBuilder(temp_config, config_file_path=self._config_path)
            plan = temp_builder.build_plan()
        else:
            plan = builder.build_plan()

        return plan

    def profile(
        self,
        table_patterns: Optional[List[TablePattern]] = None,
        dry_run: bool = False,
        progress_callback: Optional[Any] = None,
    ) -> List["ProfilingResult"]:
        """
        Profile tables and write results to storage.

        Args:
            table_patterns: Optional list of table patterns to profile
                          (uses config if not provided). Patterns will be expanded.
            dry_run: If True, profile but don't write to storage
            progress_callback: Optional callback function(current, total, table_name)
                             called when starting each table

        Returns:
            List of ProfilingResult objects

        Example:
            >>> results = client.profile()
            >>> for result in results:
            ...     print(f"Profiled {result.dataset_name}: {len(result.columns)} columns")
        """
        from .planner import PlanBuilder
        from .profiling.core import ProfileEngine
        from .storage.writer import ResultWriter

        # Expand patterns if provided
        if table_patterns:
            builder = PlanBuilder(self._config, config_file_path=self._config_path)
            expanded_patterns = builder.expand_table_patterns(table_patterns)
            if not expanded_patterns:
                logger.warning("No tables found matching provided patterns")
                return []
            table_patterns = expanded_patterns

        # Create event bus
        event_bus = self._get_event_bus()

        # Create profiling engine
        engine = ProfileEngine(self._config, event_bus=event_bus)
        results = engine.profile(table_patterns=table_patterns, progress_callback=progress_callback)

        if not dry_run and results:
            # Write results to storage
            writer = ResultWriter(
                self._config.storage,
                baselinr_config=self._config,
                event_bus=event_bus,
            )
            try:
                writer.write_results(
                    results,
                    environment=self._config.environment,
                    enable_enrichment=self._config.profiling.enable_enrichment,
                )
            finally:
                writer.close()

        return results

    def detect_drift(
        self,
        dataset_name: str,
        baseline_run_id: Optional[str] = None,
        current_run_id: Optional[str] = None,
        schema_name: Optional[str] = None,
    ) -> "DriftReport":
        """
        Detect drift between profiling runs.

        Args:
            dataset_name: Name of the dataset/table
            baseline_run_id: Optional run ID to use as baseline
                           (default: auto-selected based on strategy)
            current_run_id: Optional run ID to compare against baseline
                          (default: latest run)
            schema_name: Optional schema name

        Returns:
            DriftReport object with detected drift details

        Example:
            >>> report = client.detect_drift("customers")
            >>> print(f"Found {len(report.column_drifts)} column drifts")
            >>> print(f"Schema changes: {report.schema_changes}")
        """
        from .drift.detector import DriftDetector

        # Create event bus
        event_bus = self._get_event_bus()

        # Create drift detector
        detector = DriftDetector(
            self._config.storage,
            self._config.drift_detection,
            event_bus=event_bus,
            retry_config=self._config.retry,
            metrics_enabled=self._config.monitoring.enable_metrics,
        )

        # Detect drift
        report = detector.detect_drift(
            dataset_name=dataset_name,
            baseline_run_id=baseline_run_id,
            current_run_id=current_run_id,
            schema_name=schema_name,
        )

        return report

    def query_runs(
        self,
        schema: Optional[str] = None,
        table: Optional[str] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        days: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List["RunSummary"]:
        """
        Query profiling runs with filters.

        Args:
            schema: Filter by schema name
            table: Filter by table name
            status: Filter by status
            environment: Filter by environment
            days: Number of days to look back
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of RunSummary objects

        Example:
            >>> runs = client.query_runs(days=7, limit=10)
            >>> for run in runs:
            ...     print(f"{run.dataset_name}: {run.profiled_at}")
        """
        client = self._ensure_query_client()
        return client.query_runs(
            schema=schema,
            table=table,
            status=status,
            environment=environment,
            days=days,
            limit=limit,
            offset=offset,
        )

    def query_drift(
        self,
        table: Optional[str] = None,
        schema: Optional[str] = None,
        severity: Optional[str] = None,
        days: int = 7,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Any]:
        """
        Query drift events.

        Args:
            table: Filter by table name
            schema: Filter by schema name
            severity: Filter by severity (low/medium/high)
            days: Number of days to look back
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of drift event objects

        Example:
            >>> drift_events = client.query_drift(table="customers", severity="high", days=7)
            >>> for event in drift_events:
            ...     print(f"Drift in {event.column_name}: {event.change_percent}%")
        """
        client = self._ensure_query_client()
        return client.query_drift_events(
            table=table,
            severity=severity,
            days=days,
            limit=limit,
            offset=offset,
        )

    def query_anomalies(
        self,
        table: Optional[str] = None,
        schema: Optional[str] = None,
        run_id: Optional[str] = None,
        severity: Optional[str] = None,
        days: int = 7,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Query anomaly events.

        Anomalies are automatically detected during profiling (if enabled in config).
        This method queries existing anomaly events.

        Args:
            table: Filter by table name
            schema: Filter by schema name
            run_id: Filter by specific run ID
            severity: Filter by severity (low/medium/high)
            days: Number of days to look back
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of anomaly event dictionaries

        Example:
            >>> anomalies = client.query_anomalies(table="customers", severity="high", days=7)
            >>> for anomaly in anomalies:
            ...     print(f"Anomaly in {anomaly['column_name']}: {anomaly['actual_value']}")
        """
        client = self._ensure_query_client()

        # Query all AnomalyDetected events
        events = []
        if run_id:
            # Query events for specific run
            run_events = client.query_run_events(run_id, event_types=["AnomalyDetected"])
            events.extend(run_events)
        else:
            # Query all anomaly events from events table
            # We'll need to query the events table directly since there's no dedicated method
            from datetime import datetime, timedelta

            from sqlalchemy import text

            conditions = ["event_type = 'AnomalyDetected'"]
            params: Dict[str, Any] = {}

            if table:
                conditions.append("table_name = :table")
                params["table"] = table

            if severity:
                # Anomaly events store severity in metadata, we'll filter post-query
                # or check if there's a severity field
                conditions.append("metadata::text LIKE :severity_pattern")
                params["severity_pattern"] = f'%"severity":"{severity}"%'

            if days:
                conditions.append("timestamp > :start_date")
                params["start_date"] = datetime.utcnow() - timedelta(days=days)

            where_clause = " AND ".join(conditions)

            query = text(
                f"""
                SELECT event_id, event_type, run_id, table_name, column_name, metric_name,
                       baseline_value, current_value, change_percent, drift_severity,
                       timestamp, metadata
                FROM {client.events_table}
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """
            )

            params["limit"] = limit
            params["offset"] = offset

            with client.engine.connect() as conn:
                results = conn.execute(query, params).fetchall()
                for row in results:
                    timestamp_val: datetime
                    if isinstance(row[10], str):
                        timestamp_val = datetime.fromisoformat(row[10])
                    elif isinstance(row[10], datetime):
                        timestamp_val = row[10]
                    else:
                        continue

                    # Parse metadata if it's a JSON string
                    metadata = row[11] if row[11] else {}
                    if isinstance(metadata, str):
                        try:
                            import json

                            metadata = json.loads(metadata)
                        except (json.JSONDecodeError, ValueError):
                            metadata = {}

                    event = {
                        "event_id": str(row[0]),
                        "event_type": str(row[1]) if row[1] else None,
                        "run_id": str(row[2]) if row[2] else None,
                        "table_name": str(row[3]) if row[3] else None,
                        "column_name": str(row[4]) if row[4] else None,
                        "metric_name": str(row[5]) if row[5] else None,
                        "baseline_value": float(row[6]) if row[6] is not None else None,
                        "current_value": float(row[7]) if row[7] is not None else None,
                        "change_percent": float(row[8]) if row[8] is not None else None,
                        "drift_severity": str(row[9]) if row[9] else None,
                        "timestamp": timestamp_val,
                        "metadata": metadata,
                    }

                    # Extract severity from metadata if available
                    if severity and "severity" in metadata:
                        if metadata.get("severity") != severity:
                            continue

                    events.append(event)

        # Apply schema filter post-query if needed (since events table may not have schema field)
        if schema:
            # Schema is typically stored in metadata or we'd need to join with runs table
            # For now, we'll return all events (schema filtering would require more complex query)
            logger.debug("Schema filtering for anomalies requires joining with runs table")

        return events[:limit]

    def query_run_details(
        self, run_id: str, dataset_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific run.

        Args:
            run_id: Run ID to query
            dataset_name: Optional dataset name (required if run has multiple tables)

        Returns:
            Dictionary with run metadata and metrics, or None if not found

        Example:
            >>> details = client.query_run_details("abc-123-def")
            >>> print(f"Run profiled {details['run']['row_count']} rows")
        """
        client = self._ensure_query_client()
        return client.query_run_details(run_id, dataset_name=dataset_name)

    def query_table_history(
        self, table: str, schema: Optional[str] = None, days: int = 30, limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get profiling history for a table over time.

        Args:
            table: Table name
            schema: Optional schema name
            days: Number of days of history
            limit: Maximum results to return

        Returns:
            Dictionary with table history data

        Example:
            >>> history = client.query_table_history("customers", days=90)
            >>> print(f"Found {history['run_count']} historical runs")
        """
        client = self._ensure_query_client()
        return client.query_table_history(table_name=table, schema_name=schema, days=days)

    def get_upstream_lineage(
        self,
        table: str,
        schema: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get upstream lineage for a table.

        Args:
            table: Table name
            schema: Optional schema name
            max_depth: Maximum depth to traverse (None = unlimited)

        Returns:
            List of upstream tables with depth information

        Example:
            >>> upstream = client.get_upstream_lineage("customers", max_depth=2)
            >>> print(f"Found {len(upstream)} upstream dependencies")
        """
        client = self._ensure_query_client()
        return client.query_lineage_upstream(table, schema, max_depth)

    def get_downstream_lineage(
        self,
        table: str,
        schema: Optional[str] = None,
        max_depth: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get downstream lineage for a table.

        Args:
            table: Table name
            schema: Optional schema name
            max_depth: Maximum depth to traverse (None = unlimited)

        Returns:
            List of downstream tables with depth information

        Example:
            >>> downstream = client.get_downstream_lineage("customers")
            >>> print(f"Found {len(downstream)} downstream dependencies")
        """
        client = self._ensure_query_client()
        return client.query_lineage_downstream(table, schema, max_depth)

    def get_lineage_path(
        self,
        from_table: str,
        to_table: str,
        from_schema: Optional[str] = None,
        to_schema: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get lineage path between two tables.

        Args:
            from_table: Source table name
            to_table: Target table name
            from_schema: Optional source schema
            to_schema: Optional target schema

        Returns:
            List of tables in the path, or empty list if no path found

        Example:
            >>> path = client.get_lineage_path("raw.events", "analytics.revenue")
            >>> print(f"Path length: {len(path)}")
        """
        client = self._ensure_query_client()
        return client.query_lineage_path(from_table, to_table, from_schema, to_schema)

    def get_available_lineage_providers(self) -> List[str]:
        """
        Get list of available lineage providers.

        Returns:
            List of provider names that are currently available

        Example:
            >>> providers = client.get_available_lineage_providers()
            >>> print(f"Available providers: {providers}")
        """
        try:
            from .integrations.lineage import LineageProviderRegistry

            registry = LineageProviderRegistry()
            providers = registry.get_available_providers()
            return [p.get_provider_name() for p in providers]
        except Exception as e:
            logger.debug(f"Could not get lineage providers: {e}")
            return []

    def get_status(
        self, drift_only: bool = False, days: int = 7, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get status summary (recent runs + drift summary).

        Args:
            drift_only: If True, only return drift summary
            days: Number of days to look back for runs
            limit: Maximum number of recent runs to include

        Returns:
            Dictionary with runs_data and drift_summary (JSON-serializable)

        Example:
            >>> status = client.get_status()
            >>> print(f"Active drift events: {len(status['drift_summary'])}")
            >>> print(f"Recent runs: {len(status['runs_data'])}")
        """
        from datetime import datetime

        from sqlalchemy import text

        client = self._ensure_query_client()

        # Query recent runs (default: last 7 days, or limit)
        runs = client.query_runs(days=days, limit=limit)

        # Enrich runs with event data
        runs_data = []
        for run in runs:
            # Query events for this run
            events = client.query_run_events(
                run.run_id, event_types=["ProfilingCompleted", "AnomalyDetected"]
            )

            # Extract duration from ProfilingCompleted event
            duration = "N/A"
            for event in events:
                if event.get("event_type") == "ProfilingCompleted":
                    metadata = event.get("metadata", {})
                    if isinstance(metadata, dict):
                        duration_seconds = metadata.get("duration_seconds")
                        if duration_seconds is not None:
                            if duration_seconds < 60:
                                duration = f"{duration_seconds:.1f}s"
                            elif duration_seconds < 3600:
                                duration = f"{duration_seconds / 60:.1f}m"
                            else:
                                duration = f"{duration_seconds / 3600:.1f}h"
                    break

            # Count anomalies
            anomalies_count = sum(
                1 for event in events if event.get("event_type") == "AnomalyDetected"
            )

            # Count metrics (query results table)
            metrics_count = 0
            try:
                with client.engine.connect() as conn:
                    metrics_query = text(
                        f"""
                        SELECT COUNT(DISTINCT metric_name)
                        FROM {client.results_table}
                        WHERE run_id = :run_id AND dataset_name = :dataset_name
                    """
                    )
                    metrics_result = conn.execute(
                        metrics_query, {"run_id": run.run_id, "dataset_name": run.dataset_name}
                    ).fetchone()
                    if metrics_result and metrics_result[0] is not None:
                        metrics_count = int(metrics_result[0])
            except Exception as e:
                logger.debug(f"Failed to count metrics: {e}")

            # Check if this table has drift
            drift_events = client.query_drift_events(table=run.dataset_name, days=7, limit=1)
            has_drift = len(drift_events) > 0
            severity = drift_events[0].drift_severity if drift_events else None

            runs_data.append(
                {
                    "run_id": run.run_id,
                    "table_name": run.dataset_name,
                    "schema_name": run.schema_name,
                    "profiled_at": (
                        run.profiled_at.isoformat()
                        if isinstance(run.profiled_at, datetime)
                        else str(run.profiled_at)
                    ),
                    "duration": duration,
                    "rows_scanned": run.row_count,
                    "sample_percent": "N/A",  # Not stored in current schema
                    "metrics_count": metrics_count,
                    "anomalies_count": anomalies_count,
                    "has_drift": has_drift,
                    "drift_severity": severity,
                    "status_indicator": (
                        "🟢"
                        if not has_drift and anomalies_count == 0
                        else ("🔴" if has_drift and severity == "high" else "🟡")
                    ),
                }
            )

        # Query active drift summary
        drift_summary = client.query_active_drift_summary(days=7)

        # Build result
        result: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "drift_summary": drift_summary,
        }

        if not drift_only:
            result["runs_data"] = runs_data

        return result

    def _ensure_migration_manager(self) -> "MigrationManager":
        """Lazy initialize migration manager and register all migrations."""
        if self._migration_manager is None:
            from .connectors.factory import create_connector
            from .storage.migrations.manager import MigrationManager
            from .storage.migrations.versions import ALL_MIGRATIONS

            connector = create_connector(self._config.storage.connection, self._config.retry)
            self._migration_manager = MigrationManager(connector.engine)

            # Register all migrations
            for migration in ALL_MIGRATIONS:
                self._migration_manager.register_migration(migration)

        return self._migration_manager

    def migrate_status(self) -> Dict[str, Any]:
        """
        Check schema migration status.

        Returns:
            Dictionary with current version and pending migrations

        Example:
            >>> status = client.migrate_status()
            >>> print(f"Current version: {status['current_version']}")
        """
        from .storage.migrations.versions import ALL_MIGRATIONS
        from .storage.schema_version import CURRENT_SCHEMA_VERSION

        manager = self._ensure_migration_manager()
        current_version = manager.get_current_version()

        # Find pending migrations
        pending_migrations = []
        if current_version is None:
            pending_migrations = [m.version for m in ALL_MIGRATIONS]
        else:
            pending_migrations = [m.version for m in ALL_MIGRATIONS if m.version > current_version]

        return {
            "current_version": current_version,
            "latest_version": CURRENT_SCHEMA_VERSION,
            "pending_migrations": pending_migrations,
            "migration_count": len(ALL_MIGRATIONS),
        }

    def migrate_apply(
        self, target_version: Optional[int] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Apply schema migrations.

        Args:
            target_version: Target schema version to migrate to (None = latest)
            dry_run: If True, preview migrations without applying

        Returns:
            Dictionary with migration results

        Example:
            >>> result = client.migrate_apply(target_version=1)
            >>> print(f"Applied migrations to version {result['target_version']}")
        """
        from .storage.migrations.versions import ALL_MIGRATIONS
        from .storage.schema_version import CURRENT_SCHEMA_VERSION

        manager = self._ensure_migration_manager()

        if target_version is None:
            target_version = CURRENT_SCHEMA_VERSION

        if dry_run:
            # Preview what would be applied
            current = manager.get_current_version() or 0
            migrations_to_apply = [
                m.version for m in ALL_MIGRATIONS if current < m.version <= target_version
            ]

            return {
                "target_version": target_version,
                "preview": True,
                "migrations_to_apply": migrations_to_apply,
                "message": f"Would apply {len(migrations_to_apply)} migrations",
            }

        # Apply migrations
        success = manager.migrate_to(target_version, dry_run=False)
        if success:
            return {
                "target_version": target_version,
                "success": True,
                "message": f"Successfully migrated to version {target_version}",
            }
        else:
            return {
                "target_version": target_version,
                "success": False,
                "message": "Migration failed",
            }

    def migrate_validate(self) -> Dict[str, Any]:
        """
        Validate schema integrity.

        Returns:
            Dictionary with validation results

        Example:
            >>> result = client.migrate_validate()
            >>> print(f"Schema valid: {result['is_valid']}")
        """
        manager = self._ensure_migration_manager()

        try:
            result = manager.validate_schema()
            return {
                "is_valid": result.get("valid", False),
                "version": result.get("version"),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
                "message": "Schema is valid" if result.get("valid") else "Schema validation failed",
            }
        except Exception as e:
            return {
                "is_valid": False,
                "message": f"Schema validation error: {str(e)}",
                "error": str(e),
            }

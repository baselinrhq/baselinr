"""
Command-line interface for Baselinr.

Provides CLI commands for profiling tables and detecting drift.
"""

import argparse
import importlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .query import MetadataQueryClient

from .config.loader import ConfigLoader
from .config.schema import BaselinrConfig, HookConfig, SamplingConfig, TablePattern
from .drift.detector import DriftDetector
from .events import EventBus, LoggingAlertHook, SnowflakeEventHook, SQLEventHook
from .incremental import IncrementalPlan, TableState, TableStateStore
from .planner import PlanBuilder, print_plan
from .profiling.core import ProfileEngine
from .storage.writer import ResultWriter
from .utils.logging import RunContext, log_event

# Setup fallback logging (will be replaced by structured logging per command)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_event_bus(config: BaselinrConfig) -> Optional[EventBus]:
    """
    Create and configure an event bus from configuration.

    Args:
        config: Baselinr configuration

    Returns:
        Configured EventBus or None if hooks are disabled
    """
    if not config.hooks.enabled or not config.hooks.hooks:
        logger.debug("Event hooks are disabled or no hooks configured")
        return None

    bus = EventBus()

    for hook_config in config.hooks.hooks:
        if not hook_config.enabled:
            logger.debug(f"Skipping disabled hook: {hook_config.type}")
            continue

        try:
            hook = _create_hook(hook_config)
            if hook:
                bus.register(hook)
                logger.info(f"Registered hook: {hook_config.type}")
        except Exception as e:
            logger.error(f"Failed to create hook {hook_config.type}: {e}")

    if bus.hook_count == 0:
        logger.warning("No hooks registered - event bus will be inactive")
        return None

    return bus


def _create_hook(hook_config: HookConfig):
    """
    Create a hook instance from configuration.

    Args:
        hook_config: Hook configuration

    Returns:
        Hook instance
    """
    if hook_config.type == "logging":
        log_level = hook_config.log_level or "INFO"
        return LoggingAlertHook(log_level=log_level)

    elif hook_config.type == "snowflake":
        if not hook_config.connection:
            raise ValueError("Snowflake hook requires connection configuration")

        # Create engine for Snowflake connection
        from .connectors import SnowflakeConnector

        snowflake_connector = SnowflakeConnector(hook_config.connection)
        table_name = hook_config.table_name or "baselinr_events"
        return SnowflakeEventHook(engine=snowflake_connector.engine, table_name=table_name)

    elif hook_config.type == "sql":
        if not hook_config.connection:
            raise ValueError("SQL hook requires connection configuration")

        # Create engine based on connection type
        from .connectors import (
            BaseConnector,
            BigQueryConnector,
            MySQLConnector,
            PostgresConnector,
            RedshiftConnector,
            SQLiteConnector,
        )

        connector: BaseConnector
        if hook_config.connection.type == "postgres":
            connector = PostgresConnector(hook_config.connection)
        elif hook_config.connection.type == "sqlite":
            connector = SQLiteConnector(hook_config.connection)
        elif hook_config.connection.type == "mysql":
            connector = MySQLConnector(hook_config.connection)
        elif hook_config.connection.type == "bigquery":
            connector = BigQueryConnector(hook_config.connection)
        elif hook_config.connection.type == "redshift":
            connector = RedshiftConnector(hook_config.connection)
        else:
            raise ValueError(f"Unsupported SQL database type: {hook_config.connection.type}")

        table_name = hook_config.table_name or "baselinr_events"
        return SQLEventHook(engine=connector.engine, table_name=table_name)

    elif hook_config.type == "slack":
        if not hook_config.webhook_url:
            raise ValueError("Slack hook requires webhook_url")

        from .events import SlackAlertHook

        return SlackAlertHook(
            webhook_url=hook_config.webhook_url,
            channel=hook_config.channel,
            username=hook_config.username or "Baselinr",
            min_severity=hook_config.min_severity or "low",
            alert_on_drift=(
                hook_config.alert_on_drift if hook_config.alert_on_drift is not None else True
            ),
            alert_on_schema_change=(
                hook_config.alert_on_schema_change
                if hook_config.alert_on_schema_change is not None
                else True
            ),
            alert_on_profiling_failure=(
                hook_config.alert_on_profiling_failure
                if hook_config.alert_on_profiling_failure is not None
                else True
            ),
            timeout=hook_config.timeout or 10,
        )

    elif hook_config.type == "custom":
        if not hook_config.module or not hook_config.class_name:
            raise ValueError("Custom hook requires module and class_name")

        # Dynamically import and instantiate custom hook
        module = importlib.import_module(hook_config.module)
        hook_class = getattr(module, hook_config.class_name)
        return hook_class(**hook_config.params)

    else:
        raise ValueError(f"Unknown hook type: {hook_config.type}")


def profile_command(args):
    """Execute profiling command."""
    log_event(
        logger,
        "command_started",
        f"Loading configuration from: {args.config}",
        metadata={"config_path": args.config, "command": "profile"},
    )

    # Initialize ctx early for error handling
    ctx = None

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)
        log_event(
            logger,
            "config_loaded",
            f"Configuration loaded for environment: {config.environment}",
            metadata={"environment": config.environment},
        )

        # Start metrics server if enabled
        metrics_enabled = config.monitoring.enable_metrics
        if metrics_enabled:
            try:
                from .utils.metrics import start_metrics_server

                start_metrics_server(config.monitoring.port)
            except ImportError:
                log_event(
                    logger,
                    "metrics_import_failed",
                    "prometheus_client not installed. Install with: pip install prometheus_client",
                    level="warning",
                )
                metrics_enabled = False
            except Exception as e:
                log_event(
                    logger,
                    "metrics_server_failed",
                    f"Failed to start metrics server: {e}",
                    level="warning",
                )
                metrics_enabled = False

        # Create run context with structured logging
        ctx = RunContext.create(component="cli", metrics_enabled=metrics_enabled)

        # Create event bus and register hooks
        event_bus = create_event_bus(config)
        if event_bus:
            log_event(
                ctx.logger,
                "event_bus_initialized",
                f"Event bus initialized with {event_bus.hook_count} hooks",
                metadata={"hook_count": event_bus.hook_count},
            )

        plan_builder = PlanBuilder(config)
        incremental_plan = plan_builder.get_tables_to_run()
        tables_to_profile = _select_tables_from_plan(incremental_plan, config)
        if not tables_to_profile:
            log_event(ctx.logger, "incremental_noop", "No tables selected for this run")
            return 0

        # Create profiling engine with run context
        engine = ProfileEngine(config, event_bus=event_bus, run_context=ctx)

        # Run profiling
        log_event(ctx.logger, "profiling_batch_started", "Starting profiling...")
        results = engine.profile(table_patterns=tables_to_profile)

        if not results:
            log_event(ctx.logger, "no_results", "No profiling results generated", level="warning")
            return 1

        log_event(
            ctx.logger,
            "profiling_batch_completed",
            f"Profiling completed: {len(results)} tables profiled",
            metadata={"table_count": len(results)},
        )

        # Write results to storage
        if not args.dry_run:
            log_event(ctx.logger, "storage_write_started", "Writing results to storage...")
            writer = ResultWriter(
                config.storage, config.retry, baselinr_config=config, event_bus=event_bus
            )
            writer.write_results(
                results,
                environment=config.environment,
                enable_enrichment=config.profiling.enable_enrichment,
            )
            log_event(
                ctx.logger,
                "storage_write_completed",
                "Results written successfully",
                metadata={"result_count": len(results)},
            )
            writer.close()
            _update_state_store_with_results(config, incremental_plan, results)
        else:
            log_event(ctx.logger, "dry_run", "Dry run - results not written to storage")

        # Output results
        if args.output:
            output_path = Path(args.output)
            with open(output_path, "w") as f:
                json.dump([r.to_dict() for r in results], f, indent=2)
            log_event(
                ctx.logger,
                "results_exported",
                f"Results saved to: {args.output}",
                metadata={"output_path": str(args.output)},
            )

        # Print summary
        for result in results:
            print(f"\n{'='*60}")
            print(f"Dataset: {result.dataset_name}")
            print(f"Run ID: {result.run_id}")
            print(f"Profiled at: {result.profiled_at}")
            print(f"Columns profiled: {len(result.columns)}")
            print(f"Row count: {result.metadata.get('row_count', 'N/A')}")

        # Keep metrics server alive if enabled (unless disabled in config)
        keep_alive = config.monitoring.keep_alive if config.monitoring.enable_metrics else False
        if metrics_enabled and keep_alive:
            import time

            log_event(
                ctx.logger,
                "metrics_server_keepalive",
                f"Profiling completed. Metrics server running on port {config.monitoring.port}",
                metadata={"port": config.monitoring.port},
            )
            print(f"\n{'='*60}")
            print("Profiling completed. Metrics server is running at:")
            print(f"  http://localhost:{config.monitoring.port}/metrics")
            print("\nPress Ctrl+C to stop the server and exit.")
            print(f"{'='*60}\n")

            try:
                while True:
                    time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                log_event(ctx.logger, "metrics_server_stopped", "Metrics server stopped by user")
                print("\nStopping metrics server...")
                return 0

        return 0

    except Exception as e:
        error_logger = ctx.logger if ctx else logger
        log_event(
            error_logger,
            "error",
            f"Profiling failed: {e}",
            level="error",
            metadata={"error": str(e), "error_type": type(e).__name__},
        )
        return 1


def drift_command(args):
    """Execute drift detection command."""
    logger.info(f"Loading configuration from: {args.config}")

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        # Start metrics server if enabled
        if config.monitoring.enable_metrics:
            from .utils.metrics import start_metrics_server

            try:
                start_metrics_server(config.monitoring.port)
            except Exception as e:
                logger.warning(f"Failed to start metrics server: {e}")

        # Create event bus and register hooks
        event_bus = create_event_bus(config)
        if event_bus:
            logger.info(f"Event bus initialized with {event_bus.hook_count} hooks")

        # Create drift detector with drift detection config and event bus
        detector = DriftDetector(
            config.storage,
            config.drift_detection,
            event_bus=event_bus,
            retry_config=config.retry,
            metrics_enabled=config.monitoring.enable_metrics,
        )

        # Detect drift
        logger.info(f"Detecting drift for dataset: {args.dataset}")
        report = detector.detect_drift(
            dataset_name=args.dataset,
            baseline_run_id=args.baseline,
            current_run_id=args.current,
            schema_name=args.schema,
        )

        # Print report
        print(f"\n{'='*60}")
        print("DRIFT DETECTION REPORT")
        print(f"{'='*60}")
        print(f"Dataset: {report.dataset_name}")
        print(f"Baseline: {report.baseline_run_id} ({report.baseline_timestamp})")
        print(f"Current: {report.current_run_id} ({report.current_timestamp})")
        print("\nSummary:")
        print(f"  Total drifts detected: {report.summary['total_drifts']}")
        print(f"  Schema changes: {report.summary['schema_changes']}")
        print(f"  High severity: {report.summary['drift_by_severity']['high']}")
        print(f"  Medium severity: {report.summary['drift_by_severity']['medium']}")
        print(f"  Low severity: {report.summary['drift_by_severity']['low']}")

        if report.schema_changes:
            print("\nSchema Changes:")
            for change in report.schema_changes:
                print(f"  - {change}")

        if report.column_drifts:
            print("\nMetric Drifts:")
            for drift in report.column_drifts:
                if drift.drift_detected:
                    severity = drift.drift_severity.upper()
                    col_metric = f"{drift.column_name}.{drift.metric_name}"
                    print(f"  [{severity}] {col_metric}")
                    print(f"    Baseline: {drift.baseline_value:.2f}")
                    print(f"    Current: {drift.current_value:.2f}")
                    if drift.change_percent is not None:
                        print(f"    Change: {drift.change_percent:+.2f}%")

        # Output to file
        if args.output:
            output_path = Path(args.output)
            with open(output_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            logger.info(f"Report saved to: {args.output}")

        # Return error code if critical drift detected
        if report.summary["has_critical_drift"] and args.fail_on_drift:
            logger.warning("Critical drift detected - exiting with error code")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Drift detection failed: {e}", exc_info=True)
        return 1


def plan_command(args):
    """Execute plan command."""
    logger.info(f"Loading configuration from: {args.config}")

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)
        logger.info(f"Configuration loaded for environment: {config.environment}")

        # Build plan
        logger.info("Building profiling execution plan...")
        builder = PlanBuilder(config)
        plan = builder.build_plan()

        # Validate plan
        warnings = builder.validate_plan(plan)
        if warnings:
            logger.warning("Plan validation warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")

        # Print plan
        output_format = args.output if hasattr(args, "output") else "text"
        verbose = args.verbose if hasattr(args, "verbose") else False

        print_plan(plan, format=output_format, verbose=verbose)

        return 0

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {args.config}")
        print(f"\nError: Configuration file not found: {args.config}")
        print("Please specify a valid configuration file with --config")
        return 1

    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        print(f"\nError: {e}")
        print("\nPlease check your configuration file and ensure:")
        print("  - The 'profiling.tables' section is not empty")
        print("  - All required fields are present")
        print("  - Table names are valid")
        return 1

    except Exception as e:
        logger.error(f"Plan generation failed: {e}", exc_info=True)
        print(f"\nError: Plan generation failed: {e}")
        return 1


def query_command(args):
    """Execute query command."""
    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        # Create query client
        from .connectors.factory import create_connector
        from .query import MetadataQueryClient, format_drift, format_runs, format_table_history

        connector = create_connector(config.storage.connection, config.retry)
        client = MetadataQueryClient(
            connector.engine,
            runs_table=config.storage.runs_table,
            results_table=config.storage.results_table,
            events_table="baselinr_events",
        )

        # Execute subcommand
        if args.query_command == "runs":
            runs = client.query_runs(
                schema=args.schema,
                table=args.table,
                status=args.status,
                environment=args.environment,
                days=args.days,
                limit=args.limit,
                offset=args.offset,
            )

            output = format_runs(runs, format=args.format)
            print(output)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")

        elif args.query_command == "drift":
            events = client.query_drift_events(
                table=args.table,
                severity=args.severity,
                days=args.days,
                limit=args.limit,
                offset=args.offset,
            )

            output = format_drift(events, format=args.format)
            print(output)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")

        elif args.query_command == "run":
            details = client.query_run_details(args.run_id, dataset_name=args.table)

            if not details:
                print(f"Run {args.run_id} not found")
                return 1

            if args.format == "json":
                output = json.dumps(details, indent=2, default=str)
            else:
                # Pretty print for table format
                output = f"""
RUN DETAILS
{'=' * 80}
Run ID: {details['run_id']}
Dataset: {details['dataset_name']}
Schema: {details.get('schema_name') or 'N/A'}
Profiled: {details['profiled_at']}
Status: {details['status']}
Environment: {details.get('environment') or 'N/A'}
Row Count: {details['row_count']:,}
Column Count: {details['column_count']}

COLUMN METRICS:
"""
                for col in details["columns"]:
                    output += f"\n  {col['column_name']} ({col['column_type']}):\n"
                    for metric, value in col["metrics"].items():
                        output += f"    {metric}: {value}\n"

            print(output)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")

        elif args.query_command == "table":
            history = client.query_table_history(
                args.table, schema_name=args.schema, days=args.days
            )

            output = format_table_history(history, format=args.format)
            print(output)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")

        return 0

    except Exception as e:
        logger.error(f"Query command failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1


def ui_command(args):
    """Execute UI command."""
    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        # Import UI startup function
        from .ui import start_dashboard_foreground
        from .ui.dependencies import check_all_dependencies

        # Check dependencies first
        check_all_dependencies(config, args.port_backend, args.port_frontend, args.host)

        # Start dashboard in foreground
        start_dashboard_foreground(
            config,
            backend_port=args.port_backend,
            frontend_port=args.port_frontend,
            backend_host=args.host,
        )
        return 0
    except KeyboardInterrupt:
        logger.info("UI command interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"UI command failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1


def status_command(args):
    """Execute status command."""
    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        # Create query client
        from .connectors.factory import create_connector
        from .query import MetadataQueryClient

        connector = create_connector(config.storage.connection, config.retry)
        client = MetadataQueryClient(
            connector.engine,
            runs_table=config.storage.runs_table,
            results_table=config.storage.results_table,
            events_table="baselinr_events",
        )

        # Determine output format
        output_format = "json" if args.json else "rich"

        # Watch mode
        if args.watch is not None:
            watch_interval = args.watch if args.watch > 0 else 5
            return _status_watch_mode(
                client,
                config,
                output_format,
                args.drift_only,
                args.limit,
                args.days,
                watch_interval,
            )

        # Single run
        return _status_single_run(
            client, config, output_format, args.drift_only, args.limit, args.days
        )

    except Exception as e:
        logger.error(f"Status command failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1


def _status_single_run(
    client: "MetadataQueryClient",
    config: BaselinrConfig,
    output_format: str,
    drift_only: bool,
    limit: int,
    days: int = 7,
) -> int:
    """Execute a single status check."""
    from .query.status_formatter import format_status

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
        anomalies_count = sum(1 for event in events if event.get("event_type") == "AnomalyDetected")

        # Count metrics (query results table)
        metrics_count = 0
        try:
            from sqlalchemy import text

            with client.engine.connect() as conn:
                metrics_query = text(
                    f"""
                    SELECT COUNT(DISTINCT metric_name)
                    FROM {client.results_table}
                    WHERE run_id = :run_id AND dataset_name = :dataset_name
                """
                )
                result = conn.execute(
                    metrics_query, {"run_id": run.run_id, "dataset_name": run.dataset_name}
                ).fetchone()
                if result and result[0]:
                    metrics_count = int(result[0])
        except Exception as e:
            logger.debug(f"Failed to count metrics: {e}")

        # Determine status indicator
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
                # Keep legacy status_indicator for text/JSON formats
                "status_indicator": (
                    "🟢"
                    if not has_drift and anomalies_count == 0
                    else ("🔴" if has_drift and severity == "high" else "🟡")
                ),
            }
        )

    # Query active drift summary
    drift_summary = client.query_active_drift_summary(days=7)

    # Format and display
    output = format_status(runs_data, drift_summary, format=output_format, drift_only=drift_only)
    print(output)

    return 0


def _status_watch_mode(
    client: "MetadataQueryClient",
    config: BaselinrConfig,
    output_format: str,
    drift_only: bool,
    limit: int,
    days: int = 7,
    interval: int = 5,
) -> int:
    """Execute status command in watch mode."""
    try:
        from rich.align import Align
        from rich.console import Console
        from rich.live import Live

        console = Console()

        def generate_status_renderable():
            """Generate Rich renderable for current state."""
            # Query recent runs
            runs = client.query_runs(days=days, limit=limit)

            # Enrich runs (same logic as single run)
            runs_data = []
            for run in runs:
                events = client.query_run_events(
                    run.run_id, event_types=["ProfilingCompleted", "AnomalyDetected"]
                )

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

                anomalies_count = sum(
                    1 for event in events if event.get("event_type") == "AnomalyDetected"
                )

                metrics_count = 0
                try:
                    from sqlalchemy import text

                    with client.engine.connect() as conn:
                        metrics_query = text(
                            f"""
                            SELECT COUNT(DISTINCT metric_name)
                            FROM {client.results_table}
                            WHERE run_id = :run_id AND dataset_name = :dataset_name
                        """
                        )
                        result = conn.execute(
                            metrics_query,
                            {"run_id": run.run_id, "dataset_name": run.dataset_name},
                        ).fetchone()
                        if result and result[0]:
                            metrics_count = int(result[0])
                except Exception:
                    pass

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
                        "sample_percent": "N/A",
                        "metrics_count": metrics_count,
                        "anomalies_count": anomalies_count,
                        "has_drift": has_drift,
                        "drift_severity": severity,
                        # Keep legacy status_indicator for text/JSON formats
                        "status_indicator": (
                            "🟢"
                            if not has_drift and anomalies_count == 0
                            else ("🔴" if has_drift and severity == "high" else "🟡")
                        ),
                    }
                )

            drift_summary = client.query_active_drift_summary(days=7)
            from .query.status_formatter import format_status

            # For watch mode, we need to return a Rich renderable, not a string
            # So we'll use the formatter but render it differently
            if output_format == "json":
                # For JSON, just print and return
                output = format_status(
                    runs_data, drift_summary, format="json", drift_only=drift_only
                )
                return Align.center(output)
            else:
                # For rich format, we need to create the renderables directly
                from rich.panel import Panel
                from rich.table import Table
                from rich.text import Text

                # Build the status display
                status_parts = []

                # Header
                last_updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                header = Panel.fit(
                    f"[bold]Baselinr Status[/bold] - [dim]Refreshing every {interval}s[/dim]\n"
                    f"[dim]Last updated: {last_updated}[/dim]",
                    border_style="blue",
                )
                status_parts.append(header)

                # Recent Runs Section
                if not drift_only:
                    runs_table = Table(
                        title="Recent Profiling Runs", show_header=True, header_style="bold magenta"
                    )
                    runs_table.add_column("Table", style="cyan", no_wrap=True)
                    runs_table.add_column("Schema", style="dim")
                    runs_table.add_column("Duration", justify="right")
                    runs_table.add_column("Rows", justify="right")
                    runs_table.add_column("Metrics", justify="right")
                    runs_table.add_column("Anomalies", justify="right")
                    runs_table.add_column("Status", justify="center")

                    if not runs_data:
                        runs_table.add_row("[dim]No runs found[/dim]", "", "", "", "", "", "")
                    else:
                        for run in runs_data:
                            table_name = run.get("table_name", "N/A")
                            schema_name = run.get("schema_name") or "[dim]-[/dim]"
                            duration = run.get("duration", "N/A")
                            rows = (
                                f"{run.get('rows_scanned', 0):,}"
                                if run.get("rows_scanned")
                                else "[dim]N/A[/dim]"
                            )
                            metrics = str(run.get("metrics_count", 0))
                            anomalies = str(run.get("anomalies_count", 0))
                            status = run.get("status_indicator", "🟢")

                            runs_table.add_row(
                                table_name, schema_name, duration, rows, metrics, anomalies, status
                            )

                    status_parts.append(runs_table)

                # Drift Summary Section
                drift_table = Table(
                    title="Active Drift Summary", show_header=True, header_style="bold yellow"
                )
                drift_table.add_column("Table", style="cyan", no_wrap=True)
                drift_table.add_column("Severity", justify="center")
                drift_table.add_column("Type", style="dim")
                drift_table.add_column("Started", style="dim")
                drift_table.add_column("Events", justify="right")

                if not drift_summary:
                    drift_table.add_row("[dim]No active drift detected[/dim]", "", "", "", "")
                else:
                    for drift in drift_summary:
                        table_name = drift.get("table_name", "N/A")
                        severity = drift.get("severity", "unknown")
                        drift_type = drift.get("drift_type", "unknown")
                        started_at = drift.get("started_at", "N/A")
                        event_count = str(drift.get("event_count", 0))

                        # Color code severity
                        if severity == "high":
                            severity_text = Text(severity.upper(), style="bold red")
                        elif severity == "medium":
                            severity_text = Text(severity.upper(), style="bold yellow")
                        elif severity == "low":
                            severity_text = Text(severity.upper(), style="yellow")
                        else:
                            severity_text = Text(severity, style="dim")

                        # Format started_at timestamp
                        if started_at and started_at != "N/A":
                            try:
                                dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                                started_at = dt.strftime("%Y-%m-%d %H:%M")
                            except (ValueError, AttributeError):
                                pass

                        drift_table.add_row(
                            table_name, severity_text, drift_type, started_at, event_count
                        )

                status_parts.append(drift_table)

                # Combine all parts
                from rich.console import Group

                return Group(*status_parts)

        # Watch loop
        import time

        try:
            with Live(
                generate_status_renderable(),
                refresh_per_second=1.0 / interval if interval > 0 else 0.2,
                console=console,
                screen=False,
            ) as live:
                while True:
                    time.sleep(interval)
                    live.update(generate_status_renderable())
        except KeyboardInterrupt:
            console.print("\n[dim]Watch mode stopped[/dim]")
            return 0

    except ImportError:
        logger.error("Rich library required for watch mode. Install with: pip install rich")
        print("\nError: Watch mode requires Rich library")
        return 1
    except Exception as e:
        logger.error(f"Watch mode failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1


def migrate_command(args):
    """Execute schema migration command."""
    logger.info(f"Loading configuration from: {args.config}")

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        # Create migration manager
        from .connectors.factory import create_connector
        from .storage.migrations import MigrationManager
        from .storage.migrations.versions import ALL_MIGRATIONS

        connector = create_connector(config.storage.connection, config.retry)
        manager = MigrationManager(connector.engine)

        # Register all migrations
        for migration in ALL_MIGRATIONS:
            manager.register_migration(migration)

        # Execute subcommand
        if args.migrate_command == "status":
            current = manager.get_current_version()
            from .storage.schema_version import CURRENT_SCHEMA_VERSION

            print(f"\n{'='*60}")
            print("SCHEMA VERSION STATUS")
            print(f"{'='*60}")
            print(f"Current database version: {current or 'not initialized'}")
            print(f"Current code version: {CURRENT_SCHEMA_VERSION}")

            if current is None:
                print("\n⚠️  Schema version not initialized")
                print("Run: baselinr migrate apply --target 1")
            elif current < CURRENT_SCHEMA_VERSION:
                print(f"\n⚠️  Database schema is behind (v{current} < v{CURRENT_SCHEMA_VERSION})")
                print(f"Run: baselinr migrate apply --target {CURRENT_SCHEMA_VERSION}")
            elif current > CURRENT_SCHEMA_VERSION:
                print(f"\n❌ Database schema is ahead (v{current} > v{CURRENT_SCHEMA_VERSION})")
                print("Update Baselinr package to match database version")
            else:
                print("\n✅ Schema version is up to date")

        elif args.migrate_command == "apply":
            target = args.target
            dry_run = args.dry_run

            if dry_run:
                print("🔍 DRY RUN MODE - No changes will be applied\n")

            success = manager.migrate_to(target, dry_run=dry_run)

            if success:
                if not dry_run:
                    print(f"\n✅ Successfully migrated to version {target}")
                return 0
            else:
                print("\n❌ Migration failed")
                return 1

        elif args.migrate_command == "validate":
            print("Validating schema integrity...\n")
            results = manager.validate_schema()

            print(f"Schema Version: {results['version']}")
            print(f"Valid: {'✅ Yes' if results['valid'] else '❌ No'}\n")

            if results["errors"]:
                print("Errors:")
                for error in results["errors"]:
                    print(f"  ❌ {error}")
                print()

            if results["warnings"]:
                print("Warnings:")
                for warning in results["warnings"]:
                    print(f"  ⚠️  {warning}")
                print()

            return 0 if results["valid"] else 1

        return 0

    except Exception as e:
        logger.error(f"Migration command failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Baselinr - Data profiling and drift detection")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Plan command
    plan_parser = subparsers.add_parser("plan", help="Build and display profiling execution plan")
    plan_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file (YAML or JSON)"
    )
    plan_parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    plan_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose details including metrics and configuration",
    )

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Profile datasets")
    profile_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file (YAML or JSON)"
    )
    profile_parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    profile_parser.add_argument(
        "--dry-run", action="store_true", help="Run profiling without writing to storage"
    )

    # Drift command
    drift_parser = subparsers.add_parser("drift", help="Detect drift between runs")
    drift_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file (YAML or JSON)"
    )
    drift_parser.add_argument(
        "--dataset", "-d", required=True, help="Dataset name to check for drift"
    )
    drift_parser.add_argument("--baseline", "-b", help="Baseline run ID (default: second-latest)")
    drift_parser.add_argument("--current", help="Current run ID (default: latest)")
    drift_parser.add_argument("--schema", "-s", help="Schema name")
    drift_parser.add_argument("--output", "-o", help="Output file for report (JSON)")
    drift_parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit with error code if critical drift detected",
    )

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Manage schema migrations")
    migrate_subparsers = migrate_parser.add_subparsers(
        dest="migrate_command", help="Migration operation"
    )

    # migrate status
    status_parser = migrate_subparsers.add_parser("status", help="Show current schema version")
    status_parser.add_argument("--config", "-c", required=True, help="Path to configuration file")

    # migrate apply
    apply_parser = migrate_subparsers.add_parser("apply", help="Apply migrations")
    apply_parser.add_argument("--config", "-c", required=True, help="Path to configuration file")
    apply_parser.add_argument("--target", type=int, required=True, help="Target schema version")
    apply_parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying"
    )

    # migrate validate
    validate_parser = migrate_subparsers.add_parser("validate", help="Validate schema integrity")
    validate_parser.add_argument("--config", "-c", required=True, help="Path to configuration file")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query profiling metadata")
    query_subparsers = query_parser.add_subparsers(dest="query_command", help="Query type")

    # query runs
    runs_parser = query_subparsers.add_parser("runs", help="Query profiling runs")
    runs_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    runs_parser.add_argument("--schema", help="Filter by schema name")
    runs_parser.add_argument("--table", help="Filter by table name")
    runs_parser.add_argument("--status", choices=["completed", "failed"], help="Filter by status")
    runs_parser.add_argument("--environment", help="Filter by environment")
    runs_parser.add_argument("--days", type=int, default=30, help="Days to look back (default: 30)")
    runs_parser.add_argument("--limit", type=int, default=100, help="Max results (default: 100)")
    runs_parser.add_argument("--offset", type=int, default=0, help="Pagination offset")
    runs_parser.add_argument(
        "--format", choices=["table", "json", "csv"], default="table", help="Output format"
    )
    runs_parser.add_argument("--output", "-o", help="Output file")

    # query drift
    drift_query_parser = query_subparsers.add_parser("drift", help="Query drift events")
    drift_query_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    drift_query_parser.add_argument("--table", help="Filter by table name")
    drift_query_parser.add_argument(
        "--severity", choices=["low", "medium", "high"], help="Filter by severity"
    )
    drift_query_parser.add_argument(
        "--days", type=int, default=30, help="Days to look back (default: 30)"
    )
    drift_query_parser.add_argument(
        "--limit", type=int, default=100, help="Max results (default: 100)"
    )
    drift_query_parser.add_argument("--offset", type=int, default=0, help="Pagination offset")
    drift_query_parser.add_argument(
        "--format", choices=["table", "json", "csv"], default="table", help="Output format"
    )
    drift_query_parser.add_argument("--output", "-o", help="Output file")

    # query run (specific run details)
    run_parser = query_subparsers.add_parser("run", help="Query specific run details")
    run_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    run_parser.add_argument("--run-id", required=True, help="Run ID to query")
    run_parser.add_argument("--table", help="Dataset name (if run has multiple tables)")
    run_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )
    run_parser.add_argument("--output", "-o", help="Output file")

    # query table (table history)
    table_parser = query_subparsers.add_parser("table", help="Query table profiling history")
    table_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    table_parser.add_argument("--table", required=True, help="Table name")
    table_parser.add_argument("--schema", help="Schema name")
    table_parser.add_argument("--days", type=int, default=30, help="Days of history (default: 30)")
    table_parser.add_argument(
        "--format", choices=["table", "json", "csv"], default="table", help="Output format"
    )
    table_parser.add_argument("--output", "-o", help="Output file")

    # Status command
    status_parser = subparsers.add_parser(
        "status", help="Show recent profiling runs and drift summary"
    )
    status_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file (YAML or JSON)"
    )
    status_parser.add_argument(
        "--drift-only", action="store_true", help="Show only drift summary, skip runs section"
    )
    status_parser.add_argument(
        "--limit", type=int, default=20, help="Limit number of runs shown (default: 20)"
    )
    status_parser.add_argument(
        "--days", type=int, default=7, help="Number of days to look back for runs (default: 7)"
    )
    status_parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    status_parser.add_argument(
        "--watch",
        type=int,
        nargs="?",
        const=5,
        help="Auto-refresh every N seconds (default: 5). Use --watch 0 to disable.",
    )

    # UI command
    ui_parser = subparsers.add_parser("ui", help="Start local dashboard")
    ui_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file (YAML or JSON)"
    )
    ui_parser.add_argument(
        "--port-backend",
        type=int,
        default=8000,
        help="Backend API port (default: 8000)",
    )
    ui_parser.add_argument(
        "--port-frontend",
        type=int,
        default=3000,
        help="Frontend UI port (default: 3000)",
    )
    ui_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Backend host (default: 0.0.0.0)",
    )

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "plan":
        return plan_command(args)
    elif args.command == "profile":
        return profile_command(args)
    elif args.command == "drift":
        return drift_command(args)
    elif args.command == "migrate":
        if not args.migrate_command:
            migrate_parser.print_help()
            return 1
        return migrate_command(args)
    elif args.command == "query":
        if not args.query_command:
            query_parser.print_help()
            return 1
        return query_command(args)
    elif args.command == "status":
        return status_command(args)
    elif args.command == "ui":
        return ui_command(args)
    else:
        parser.print_help()
        return 1


def _select_tables_from_plan(plan: IncrementalPlan, config: BaselinrConfig):
    """Convert plan decisions into table patterns for execution."""
    selected = []
    for decision in plan.decisions:
        if decision.action not in ("full", "partial", "sample"):
            continue
        pattern = decision.table
        table_pattern = pattern.model_copy(deep=True)

        if decision.action == "partial" and decision.changed_partitions:
            if not table_pattern.partition or not table_pattern.partition.key:
                logger.warning(
                    "Partial run requested for %s but no partition key configured; "
                    "falling back to full scan",
                    pattern.table,
                )
            else:
                table_pattern.partition.strategy = "specific_values"
                table_pattern.partition.values = decision.changed_partitions

        if decision.action == "sample":
            sample_fraction = config.incremental.cost_controls.sample_fraction
            table_pattern.sampling = SamplingConfig(
                enabled=True,
                method="random",
                fraction=sample_fraction,
                max_rows=None,
            )

        selected.append(table_pattern)
    return selected


def _update_state_store_with_results(config: BaselinrConfig, plan: IncrementalPlan, results):
    """Persist latest run metadata for incremental planner."""
    if not config.incremental.enabled or not results:
        return
    store = TableStateStore(
        storage_config=config.storage,
        table_name=config.incremental.change_detection.metadata_table,
        retry_config=config.retry,
        create_tables=config.storage.create_tables,
    )
    decision_map = {
        (_plan_table_key(decision.table)): decision
        for decision in plan.decisions
        if decision.action in ("full", "partial", "sample")
    }
    for result in results:
        key = _plan_table_key_raw(result.schema_name, result.dataset_name)
        decision = decision_map.get(key)
        state = TableState(
            table_name=result.dataset_name,
            schema_name=result.schema_name,
            last_run_id=result.run_id,
            snapshot_id=decision.snapshot_id if decision else None,
            change_token=None,
            decision=decision.action if decision else "full",
            decision_reason=decision.reason if decision else "manual_run",
            last_profiled_at=result.profiled_at,
            row_count=result.metadata.get("row_count"),
            bytes_scanned=decision.estimated_cost if decision else None,
            metadata=decision.metadata if decision else {},
        )
        store.upsert_state(state)


def _plan_table_key(pattern: TablePattern) -> str:
    return _plan_table_key_raw(pattern.schema_, pattern.table)


def _plan_table_key_raw(schema: Optional[str], table: str) -> str:
    return f"{schema}.{table}" if schema else table


if __name__ == "__main__":
    sys.exit(main())

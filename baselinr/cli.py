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
from .config.schema import BaselinrConfig, HookConfig, TablePattern
from .connectors.factory import create_connector
from .drift.detector import DriftDetector
from .events import EventBus, LoggingAlertHook, SnowflakeEventHook, SQLEventHook
from .incremental import IncrementalPlan, TableState, TableStateStore
from .planner import PlanBuilder, print_plan
from .profiling.core import ProfileEngine
from .storage.writer import ResultWriter
from .utils.logging import RunContext, log_event
from .validation.executor import ValidationExecutor

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
    import time

    from .cli_output import (
        create_progress_bar,
        format_run_summary,
        get_status_indicator,
        safe_print,
    )

    start_time = time.time()
    log_event(
        logger,
        "command_started",
        f"Loading configuration from: {args.config}",
        metadata={"config_path": args.config, "command": "profile"},
    )

    # Initialize ctx early for error handling
    ctx = None
    progress = None
    progress_task = None

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

        plan_builder = PlanBuilder(config, config_file_path=args.config)

        # Expand patterns before building incremental plan
        expanded_patterns = plan_builder.expand_table_patterns()
        if not expanded_patterns:
            log_event(
                ctx.logger,
                "no_tables_expanded",
                "No tables found matching patterns",
                level="error",
            )
            safe_print(
                "[red]Error: No tables found matching patterns. "
                "Check your configuration and ensure tables exist in the database.[/red]"
            )
            return 1

        # Final validation: ensure all expanded patterns have table names
        invalid = [p for p in expanded_patterns if p.table is None]
        if invalid:
            ctx.logger.error(
                f"Found {len(invalid)} invalid pattern(s) after expansion (missing table names). "
                f"These will be skipped: {invalid}"
            )
            expanded_patterns = [p for p in expanded_patterns if p.table is not None]
            if not expanded_patterns:
                ctx.logger.error("No valid patterns remaining after filtering invalid patterns")
                safe_print(
                    "[red]Error: No valid patterns remaining "
                    "after filtering invalid patterns.[/red]"
                )
                return 1

        # Pass expanded patterns to incremental planner
        incremental_plan = plan_builder.get_tables_to_run(
            current_time=None, expanded_patterns=expanded_patterns
        )
        tables_to_profile = _select_tables_from_plan(incremental_plan, config)
        if not tables_to_profile:
            log_event(
                ctx.logger,
                "incremental_noop",
                "No tables selected for this run",
                level="error",
            )
            safe_print(
                "[red]Error: No tables selected for profiling. "
                "Check incremental profiling configuration.[/red]"
            )
            return 1

        # Create profiling engine with run context
        engine = ProfileEngine(config, event_bus=event_bus, run_context=ctx)

        # Setup progress bar if we have multiple tables
        total_tables = len(tables_to_profile)
        if total_tables > 1:
            progress = create_progress_bar(total_tables, "Profiling tables")
            if progress:
                progress_task = progress.add_task("Profiling", total=total_tables)
                progress.__enter__()

        # Define progress callback
        def progress_callback(current: int, total: int, table_name: str) -> None:
            """Update progress bar when profiling each table."""
            if progress and progress_task is not None:
                progress.update(
                    progress_task,
                    completed=current,
                    description=f"Profiling: {table_name}",
                )
            # Show status indicator
            status_indicator = get_status_indicator("profiling")
            if args.debug:
                safe_print(f"{status_indicator} Profiling table {current}/{total}: {table_name}")

        # Run profiling
        log_event(ctx.logger, "profiling_batch_started", "Starting profiling...")
        if total_tables > 0:
            status_indicator = get_status_indicator("profiling")
            safe_print(f"{status_indicator} Starting profiling of {total_tables} table(s)...")

        results = engine.profile(
            table_patterns=tables_to_profile, progress_callback=progress_callback
        )

        # Close progress bar if opened
        if progress:
            if progress_task is not None:
                progress.update(progress_task, completed=total_tables)
            progress.__exit__(None, None, None)

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

        # Calculate duration and statistics
        duration = time.time() - start_time
        total_warnings = 0  # Could be enhanced to track warnings from events
        total_drifts = 0  # Could be enhanced to track drifts detected

        # Print Rich-formatted summary
        # Use total_tables (attempted) instead of len(results) (successful only)
        # to show accurate count of tables that were attempted
        summary = format_run_summary(
            duration_seconds=duration,
            tables_scanned=total_tables,
            drifts_detected=total_drifts,
            warnings=total_warnings,
            anomalies=0,  # Could be enhanced to track anomalies
        )
        safe_print()  # New line
        safe_print(summary)  # Print panel directly

        # Print detailed results if debug mode or single table
        if args.debug or len(results) == 1:
            from rich.table import Table as RichTable

            from .cli_output import get_console

            console = get_console()
            if console:
                for result in results:
                    table = RichTable(title=f"Dataset: {result.dataset_name}", show_header=True)
                    table.add_column("Property", style="cyan")
                    table.add_column("Value", style="green")
                    table.add_row("Run ID", result.run_id[:8] + "...")
                    table.add_row("Profiled at", str(result.profiled_at))
                    table.add_row("Columns profiled", str(len(result.columns)))
                    table.add_row("Row count", str(result.metadata.get("row_count", "N/A")))
                    safe_print()
                    safe_print(table)
            else:
                # Fallback to plain text
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
    from rich.panel import Panel
    from rich.table import Table as RichTable

    from .cli_output import (
        extract_histogram_data,
        format_drift_severity,
        get_status_indicator,
        render_histogram,
        safe_print,
    )

    status_indicator = get_status_indicator("drift_check")
    safe_print(f"{status_indicator} Loading configuration...")
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
            llm_config=config.llm,
        )

        # Detect drift
        safe_print(f"{status_indicator} Detecting drift for dataset: {args.dataset}")
        logger.info(f"Detecting drift for dataset: {args.dataset}")
        report = detector.detect_drift(
            dataset_name=args.dataset,
            baseline_run_id=args.baseline,
            current_run_id=args.current,
            schema_name=args.schema,
        )

        # Format report with Rich
        from .cli_output import get_console

        console = get_console()
        if console:
            # Header Panel
            header_text = "[bold]DRIFT DETECTION REPORT[/bold]\n\n"
            header_text += f"Dataset: [cyan]{report.dataset_name}[/cyan]\n"
            baseline_short = report.baseline_run_id[:8]
            header_text += (
                f"Baseline: [dim]{baseline_short}...[/dim] " f"({report.baseline_timestamp})\n"
            )
            header_text += (
                f"Current: [dim]{report.current_run_id[:8]}...[/dim] ({report.current_timestamp})"
            )
            header_panel = Panel(header_text, border_style="#4a90e2", title="[bold]Report[/bold]")
            safe_print()
            safe_print(header_panel)

            # Summary Table
            summary_table = RichTable(
                title="Summary", show_header=True, header_style="bold magenta"
            )
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", justify="right", style="green")

            summary_table.add_row("Total drifts detected", str(report.summary["total_drifts"]))
            summary_table.add_row("Schema changes", str(report.summary["schema_changes"]))
            summary_table.add_row(
                "High severity",
                f"[bold #ff8787]{report.summary['drift_by_severity']['high']}[/bold #ff8787]",
            )
            summary_table.add_row(
                "Medium severity",
                f"[bold #f4a261]{report.summary['drift_by_severity']['medium']}[/bold #f4a261]",
            )
            summary_table.add_row(
                "Low severity",
                f"[#f4a261]{report.summary['drift_by_severity']['low']}[/#f4a261]",
            )

            safe_print()
            safe_print(summary_table)

            # Schema Changes
            if report.schema_changes:
                schema_table = RichTable(
                    title="Schema Changes", show_header=True, header_style="bold yellow"
                )
                schema_table.add_column("Change", style="red")
                safe_print()
                for change in report.schema_changes:
                    schema_table.add_row(change)
                safe_print(schema_table)

            # Metric Drifts Table
            if report.column_drifts:
                drifts_table = RichTable(
                    title="Metric Drifts", show_header=True, header_style="bold yellow"
                )
                drifts_table.add_column("Column.Metric", style="cyan")
                drifts_table.add_column("Severity", justify="center")
                drifts_table.add_column("Baseline", justify="right")
                drifts_table.add_column("Current", justify="right")
                drifts_table.add_column("Change", justify="right")

                safe_print()
                for drift in report.column_drifts:
                    if drift.drift_detected:
                        col_metric = f"{drift.column_name}.{drift.metric_name}"
                        severity_text = format_drift_severity(drift.drift_severity)

                        # Format values
                        baseline_str = (
                            f"{drift.baseline_value:.2f}"
                            if isinstance(drift.baseline_value, (int, float))
                            else str(drift.baseline_value)
                        )
                        current_str = (
                            f"{drift.current_value:.2f}"
                            if isinstance(drift.current_value, (int, float))
                            else str(drift.current_value)
                        )

                        change_str = ""
                        if drift.change_percent is not None:
                            change_str = f"{drift.change_percent:+.2f}%"
                        elif drift.change_absolute is not None:
                            change_str = f"{drift.change_absolute:+.2f}"

                        drifts_table.add_row(
                            col_metric, severity_text, baseline_str, current_str, change_str
                        )

                        # Show explanation if available
                        if drift.explanation:
                            safe_print()
                            explanation_panel = Panel(
                                drift.explanation,
                                title="[bold]Explanation[/bold]",
                                border_style="#4a90e2",
                                padding=(1, 2),
                            )
                            safe_print(explanation_panel)

                        # Show histogram if available and metric is distribution-related
                        if args.debug and drift.metric_name in ["histogram", "mean", "stddev"]:
                            baseline_hist = None
                            current_hist = None
                            if drift.metadata:
                                baseline_hist = extract_histogram_data(
                                    drift.metadata.get("baseline_histogram")
                                )
                                current_hist = extract_histogram_data(
                                    drift.metadata.get("current_histogram")
                                )

                            if baseline_hist and current_hist:
                                hist_display = render_histogram(baseline_hist, current_hist)
                                if hist_display:
                                    safe_print()
                                    safe_print(
                                        Panel(
                                            hist_display,
                                            title=f"[bold]{col_metric} Distribution[/bold]",
                                            border_style="#f4a261",
                                        )
                                    )

                safe_print(drifts_table)
        else:
            # Fallback to plain text
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
                        baseline_str = (
                            f"{drift.baseline_value:.2f}"
                            if isinstance(drift.baseline_value, (int, float))
                            else str(drift.baseline_value)
                        )
                        current_str = (
                            f"{drift.current_value:.2f}"
                            if isinstance(drift.current_value, (int, float))
                            else str(drift.current_value)
                        )
                        print(f"    Baseline: {baseline_str}")
                        print(f"    Current: {current_str}")
                        if drift.change_percent is not None:
                            print(f"    Change: {drift.change_percent:+.2f}%")
                        if drift.explanation:
                            print("\n    Explanation:")
                            print(f"    {drift.explanation}")

        # Output to file
        if args.output:
            output_path = Path(args.output)
            with open(output_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            logger.info("Report saved to: %s", args.output)

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
        builder = PlanBuilder(config, config_file_path=args.config)
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


def validate_command(args):
    """Execute validation command."""
    from rich.panel import Panel
    from rich.table import Table as RichTable

    from .cli_output import get_status_indicator, safe_print

    status_indicator = get_status_indicator("validation")
    safe_print(f"{status_indicator} Loading configuration...")
    logger.info(f"Loading configuration from: {args.config}")

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        if not config.validation or not config.validation.enabled:
            safe_print("[yellow]Validation is disabled in configuration[/yellow]")
            return 0

        # Create event bus and register hooks
        event_bus = create_event_bus(config)
        if event_bus:
            logger.info(f"Event bus initialized with {event_bus.hook_count} hooks")

        # Create connectors
        source_connector = create_connector(config.source, config.retry)
        storage_connector = create_connector(config.storage.connection, config.retry)

        # Create validation executor
        executor = ValidationExecutor(
            config=config,
            source_engine=source_connector.engine,
            storage_engine=storage_connector.engine,
            event_bus=event_bus,
        )

        safe_print(f"{status_indicator} Executing validation rules...")

        # Execute validation
        results = executor.execute_validation(table_filter=args.table)

        if not results:
            safe_print("[yellow]No validation rules configured or no rules matched filter[/yellow]")
            return 0

        # Display results
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        if args.output:
            # Write results to JSON file
            import json

            output_data = {
                "summary": {
                    "total_rules": len(results),
                    "passed": passed_count,
                    "failed": failed_count,
                },
                "results": [r.to_dict() for r in results],
            }
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2, default=str)
            safe_print(f"[green]Results written to {args.output}[/green]")
        else:
            # Display results in table format
            table = RichTable(
                title="Validation Results", show_header=True, header_style="bold magenta"
            )
            table.add_column("Table", style="cyan")
            table.add_column("Column", style="dim")
            table.add_column("Rule Type", style="blue")
            table.add_column("Status", justify="center")
            table.add_column("Failed Rows", justify="right")
            table.add_column("Failure Rate", justify="right")
            table.add_column("Severity", justify="center")

            for result in results:
                status = "[green]✓ PASS[/green]" if result.passed else "[red]✗ FAIL[/red]"
                failed_rows_str = f"{result.failed_rows:,}" if result.failed_rows > 0 else "-"
                failure_rate_str = f"{result.failure_rate:.2f}%" if result.failure_rate > 0 else "-"
                severity = result.rule.severity.upper()

                table.add_row(
                    result.rule.table,
                    result.rule.column or "[dim]-[/dim]",
                    result.rule.rule_type,
                    status,
                    failed_rows_str,
                    failure_rate_str,
                    severity,
                )

            safe_print("\n")
            safe_print(table)

            # Summary panel
            summary_text = f"[bold]Total Rules:[/bold] {len(results)}\n"
            summary_text += f"[green]Passed:[/green] {passed_count}\n"
            summary_text += f"[red]Failed:[/red] {failed_count}"

            summary_panel = Panel(summary_text, title="Summary", border_style="blue")
            safe_print("\n")
            safe_print(summary_panel)

        # Exit with error code if any validations failed
        if failed_count > 0:
            return 1

        return 0

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        safe_print(f"[red]Validation failed: {e}[/red]")
        return 1


def score_command(args):
    """
    Execute score command.

    Calculate and display data quality scores for tables. Quality scores combine
    multiple dimensions (completeness, validity, consistency, freshness, uniqueness,
    accuracy) into a single actionable score (0-100).

    Examples:
        # Calculate score for a table
        baselinr score --config config.yaml --table customers

        # Export score to CSV
        baselinr score --config config.yaml --table customers --export csv --output scores.csv

        # Export score history
        baselinr score --config config.yaml --table customers \
            --history --export json --output history.json

        # Get JSON output
        baselinr score --config config.yaml --table customers --format json
    """
    from .cli_output import safe_print

    safe_print("Loading configuration...")
    logger.info(f"Loading configuration from: {args.config}")

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        # Check if quality scoring is enabled
        if not config.quality_scoring or not config.quality_scoring.enabled:
            safe_print("[yellow]Quality scoring is disabled in configuration[/yellow]")
            return 0

        # Create storage connector
        storage_connector = create_connector(config.storage.connection, config.retry)

        # Initialize quality scorer
        from .quality.scorer import QualityScorer
        from .quality.storage import QualityScoreStorage

        scorer = QualityScorer(
            engine=storage_connector.engine,
            config=config.quality_scoring,
            results_table=config.storage.results_table,
            validation_table="baselinr_validation_results",
            events_table="baselinr_events",
            runs_table=config.storage.runs_table,
        )

        storage = QualityScoreStorage(
            engine=storage_connector.engine,
            scores_table="baselinr_quality_scores",
        )

        # Create event bus for alerting
        event_bus = create_event_bus(config)
        if event_bus:
            logger.info(f"Event bus initialized with {event_bus.hook_count} hooks")

        # Calculate score(s)
        if args.table:
            # Calculate score for specific table
            safe_print(f"Calculating quality score for table: {args.table}")
            score = scorer.calculate_table_score(
                table_name=args.table,
                schema_name=args.schema,
                period_days=7,
            )

            # Get previous score for alerting (before storing new one)
            previous_score = None
            try:
                previous_score = storage.get_latest_score(args.table, args.schema)
            except Exception as e:
                logger.debug(f"Could not fetch previous score for alerting: {e}")

            # Check for threshold breaches and degradation
            if event_bus:
                try:
                    # Check threshold breaches
                    threshold_events = scorer.check_score_thresholds(score, previous_score)
                    for event in threshold_events:
                        event_bus.emit(event)
                        logger.info(
                            f"Emitted threshold breach event: "
                            f"{event.threshold_type} for {args.table}"
                        )

                    # Check score degradation
                    degradation_event = scorer.check_score_degradation(score, previous_score)
                    if degradation_event:
                        event_bus.emit(degradation_event)
                        logger.info(f"Emitted score degradation event for {args.table}")
                except Exception as e:
                    logger.warning(f"Failed to emit quality score alerts: {e}")

            # Store score if configured
            if config.quality_scoring.store_history:
                storage.store_score(score)

            # Handle export
            if args.export:
                if not args.output:
                    safe_print("[red]Error: --output is required when using --export[/red]")
                    return 1

                import csv
                import json

                if args.history:
                    # Export score history
                    try:
                        history = storage.get_score_history(
                            args.table,
                            args.schema,
                            days=config.quality_scoring.history_retention_days,
                        )
                        if not history:
                            safe_print(
                                f"[yellow]No score history found for table: {args.table}[/yellow]"
                            )
                            return 0

                        if args.export == "json":
                            output = json.dumps(
                                [s.to_dict() for s in history], indent=2, default=str
                            )
                        else:  # csv
                            # Write CSV
                            with open(args.output, "w", newline="") as f:
                                writer = csv.DictWriter(
                                    f,
                                    fieldnames=[
                                        "table_name",
                                        "schema_name",
                                        "overall_score",
                                        "completeness_score",
                                        "validity_score",
                                        "consistency_score",
                                        "freshness_score",
                                        "uniqueness_score",
                                        "accuracy_score",
                                        "status",
                                        "total_issues",
                                        "critical_issues",
                                        "warnings",
                                        "calculated_at",
                                        "period_start",
                                        "period_end",
                                    ],
                                )
                                writer.writeheader()
                                for s in history:
                                    writer.writerow(
                                        {
                                            "table_name": s.table_name,
                                            "schema_name": s.schema_name or "",
                                            "overall_score": s.overall_score,
                                            "completeness_score": s.completeness_score,
                                            "validity_score": s.validity_score,
                                            "consistency_score": s.consistency_score,
                                            "freshness_score": s.freshness_score,
                                            "uniqueness_score": s.uniqueness_score,
                                            "accuracy_score": s.accuracy_score,
                                            "status": s.status,
                                            "total_issues": s.total_issues,
                                            "critical_issues": s.critical_issues,
                                            "warnings": s.warnings,
                                            "calculated_at": s.calculated_at.isoformat(),
                                            "period_start": s.period_start.isoformat(),
                                            "period_end": s.period_end.isoformat(),
                                        }
                                    )
                            output = f"Exported {len(history)} scores to {args.output}"
                    except Exception as e:
                        logger.error(f"Failed to export score history: {e}", exc_info=True)
                        safe_print(f"[red]Failed to export score history: {e}[/red]")
                        return 1
                else:
                    # Export single score
                    if args.export == "json":
                        output = json.dumps(score.to_dict(), indent=2, default=str)
                    else:  # csv
                        # Write CSV
                        with open(args.output, "w", newline="") as f:
                            writer = csv.DictWriter(
                                f,
                                fieldnames=[
                                    "table_name",
                                    "schema_name",
                                    "overall_score",
                                    "completeness_score",
                                    "validity_score",
                                    "consistency_score",
                                    "freshness_score",
                                    "uniqueness_score",
                                    "accuracy_score",
                                    "status",
                                    "total_issues",
                                    "critical_issues",
                                    "warnings",
                                    "calculated_at",
                                    "period_start",
                                    "period_end",
                                ],
                            )
                            writer.writeheader()
                            writer.writerow(
                                {
                                    "table_name": score.table_name,
                                    "schema_name": score.schema_name or "",
                                    "overall_score": score.overall_score,
                                    "completeness_score": score.completeness_score,
                                    "validity_score": score.validity_score,
                                    "consistency_score": score.consistency_score,
                                    "freshness_score": score.freshness_score,
                                    "uniqueness_score": score.uniqueness_score,
                                    "accuracy_score": score.accuracy_score,
                                    "status": score.status,
                                    "total_issues": score.total_issues,
                                    "critical_issues": score.critical_issues,
                                    "warnings": score.warnings,
                                    "calculated_at": score.calculated_at.isoformat(),
                                    "period_start": score.period_start.isoformat(),
                                    "period_end": score.period_end.isoformat(),
                                }
                            )
                        output = f"Exported score to {args.output}"

                # Write output to file (for JSON) or print message (for CSV)
                if args.export == "json":
                    with open(args.output, "w") as f:
                        f.write(output)
                    safe_print(f"Exported score to {args.output}")
                else:
                    safe_print(output)
                logger.info(f"Score exported to {args.output}")
                return 0

            # Output results
            if args.format == "json":
                import json

                output = json.dumps(score.to_dict(), indent=2, default=str)
                safe_print(output)
            else:
                # Rich format with trend comparison
                from .cli_output import format_score_card

                # Fetch previous score for comparison
                previous_score = None
                trend_data = None
                try:
                    # Get score history and find the previous score (skip the one we just stored)
                    history = storage.get_score_history(args.table, args.schema, days=30)
                    # Filter out the current score by comparing calculated_at timestamps
                    # (allowing small time difference for database precision)
                    for hist_score in history:
                        time_diff = abs(
                            (hist_score.calculated_at - score.calculated_at).total_seconds()
                        )
                        # If timestamps are more than 1 second apart, it's a different score
                        if time_diff > 1.0:
                            previous_score = hist_score
                            break

                    if previous_score:
                        trend_data = scorer.compare_scores(score, previous_score)
                except Exception as e:
                    logger.debug(f"Could not fetch previous score for comparison: {e}")

                # Format and display score card
                score_card = format_score_card(
                    score, trend_data=trend_data, config=config.quality_scoring
                )
                if score_card:
                    safe_print(score_card)
                else:
                    # Fallback to plain text if Rich unavailable
                    safe_print(f"\nQuality Score for {args.table}")
                safe_print(f"Overall Score: {score.overall_score:.1f}/100 [{score.status}]")
                safe_print("Components:")
                safe_print(f"  Completeness: {score.completeness_score:.1f}")
                safe_print(f"  Validity: {score.validity_score:.1f}")
                safe_print(f"  Consistency: {score.consistency_score:.1f}")
                safe_print(f"  Freshness: {score.freshness_score:.1f}")
                safe_print(f"  Uniqueness: {score.uniqueness_score:.1f}")
                safe_print(f"  Accuracy: {score.accuracy_score:.1f}")
                issues_msg = (
                    f"Issues: {score.total_issues} total, "
                    f"{score.critical_issues} critical, "
                    f"{score.warnings} warnings"
                )
                safe_print(issues_msg)
        else:
            # This should not happen if --table is required, but keep as fallback
            safe_print("[red]Error: --table is required. Use --table to specify a table.[/red]")
            safe_print("\nExample: baselinr score --config config.yaml --table customers")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Score calculation failed: {e}", exc_info=True)
        safe_print(f"[red]Score calculation failed: {e}[/red]")
        return 1


def query_command(args):
    """Execute query command."""
    from .cli_output import safe_print

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
            safe_print(output)

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
            safe_print(output)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")

        elif args.query_command == "run":
            from rich.table import Table as RichTable

            from .cli_output import get_console

            details = client.query_run_details(args.run_id, dataset_name=args.table)

            if not details:
                safe_print(f"Run {args.run_id} not found")
                return 1

            if args.format == "json":
                output = json.dumps(details, indent=2, default=str)
                safe_print(output)
            else:
                console = get_console()
                if console:
                    # Use Rich Table for better formatting
                    run_table = RichTable(
                        title="Run Details", show_header=True, header_style="bold cyan"
                    )
                    run_table.add_column("Property", style="cyan")
                    run_table.add_column("Value", style="green")
                    run_table.add_row("Run ID", details["run_id"][:8] + "...")
                    run_table.add_row("Dataset", details["dataset_name"])
                    run_table.add_row("Schema", details.get("schema_name") or "N/A")
                    run_table.add_row("Profiled", str(details["profiled_at"]))
                    run_table.add_row("Status", details["status"])
                    run_table.add_row("Environment", details.get("environment") or "N/A")
                    run_table.add_row("Row Count", f"{details['row_count']:,}")
                    run_table.add_row("Column Count", str(details["column_count"]))
                    safe_print()
                    safe_print(run_table)

                    # Column metrics table
                    if details.get("columns"):
                        metrics_table = RichTable(
                            title="Column Metrics", show_header=True, header_style="bold magenta"
                        )
                        metrics_table.add_column("Column", style="cyan")
                        metrics_table.add_column("Type", style="dim")
                        metrics_table.add_column("Metrics", style="green")
                        for col in details["columns"]:
                            metrics_str = ", ".join(
                                [f"{k}: {v}" for k, v in col.get("metrics", {}).items()]
                            )
                            metrics_table.add_row(
                                col["column_name"], col.get("column_type", "N/A"), metrics_str
                            )
                        safe_print()
                        safe_print(metrics_table)
                else:
                    # Fallback to plain text
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
                    safe_print(output)

            if args.output:
                with open(args.output, "w") as f:
                    if args.format == "json":
                        f.write(output)
                    else:
                        # For table format, we need to capture the output
                        f.write(str(details))
                logger.info(f"Results saved to: {args.output}")

        elif args.query_command == "table":
            history = client.query_table_history(
                args.table, schema_name=args.schema, days=args.days
            )

            output = format_table_history(history, format=args.format)
            safe_print(output)

            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                logger.info(f"Results saved to: {args.output}")

        return 0

    except Exception as e:
        logger.error(f"Query command failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1


def lineage_visualize_command(args):
    """Execute lineage visualize command."""
    from .cli_output import safe_print

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        # Create connector and engine
        from .connectors.factory import create_connector

        connector = create_connector(config.storage.connection, config.retry)
        engine = connector.engine

        # Import visualization components
        from .visualization import LineageGraphBuilder
        from .visualization.exporters import (
            ASCIIExporter,
            GraphvizExporter,
            JSONExporter,
            MermaidExporter,
        )

        # Build graph
        safe_print(f"Building lineage graph for {args.table}...")
        builder = LineageGraphBuilder(engine)

        if args.column:
            # Column-level lineage
            graph = builder.build_column_graph(
                root_table=args.table,
                root_column=args.column,
                schema=args.schema,
                direction=args.direction,
                max_depth=args.depth,
            )
        else:
            # Table-level lineage
            graph = builder.build_table_graph(
                root_table=args.table,
                schema=args.schema,
                direction=args.direction,
                max_depth=args.depth,
            )

        # Add drift highlighting if requested
        if args.highlight_drift:
            graph = builder.add_drift_annotations(graph)

        if not graph.nodes:
            safe_print("No lineage data found for this table")
            return 0

        safe_print(f"Found {len(graph.nodes)} nodes and {len(graph.edges)} relationships\n")

        # Export based on format
        output_content = None

        if args.format == "ascii":
            exporter = ASCIIExporter(use_color=not args.no_color)
            output_content = exporter.export(graph)

        elif args.format == "mermaid":
            exporter = MermaidExporter(direction="TD" if args.direction != "downstream" else "TD")
            output_content = exporter.export(graph)
            # Wrap in markdown code block if outputting to file
            if args.output:
                output_content = f"```mermaid\n{output_content}\n```"

        elif args.format == "dot":
            exporter = GraphvizExporter(rankdir="TB" if args.direction != "downstream" else "TB")
            output_content = exporter.export_dot(graph)

        elif args.format in ("svg", "png", "pdf"):
            if not args.output:
                safe_print(f"Error: --output is required for {args.format} format")
                return 1

            exporter = GraphvizExporter()
            try:
                success = exporter.export_image(graph, args.output, format=args.format)
                if success:
                    safe_print(f"Lineage diagram saved to: {args.output}")
                    return 0
            except RuntimeError as e:
                safe_print(f"Error: {e}")
                return 1

        elif args.format == "json":
            from .visualization.layout import HierarchicalLayout

            layout = HierarchicalLayout() if args.layout else None
            exporter = JSONExporter(layout=layout)

            if args.json_format == "cytoscape":
                output_content = exporter.export_cytoscape(graph)
            elif args.json_format == "d3":
                output_content = exporter.export_d3(graph)
            else:
                output_content = exporter.export_generic(graph)

        else:
            safe_print(f"Unknown format: {args.format}")
            return 1

        # Output result
        if args.output and output_content:
            from pathlib import Path

            output_path = Path(args.output)
            output_path.write_text(output_content)
            safe_print(f"Lineage visualization saved to: {args.output}")
        elif output_content:
            safe_print(output_content)

        return 0

    except Exception as e:
        logger.error(f"Lineage visualize command failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1


def lineage_command(args):
    """Execute lineage command."""
    from .cli_output import safe_print

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        # Create query client
        from .connectors.factory import create_connector
        from .query import MetadataQueryClient

        connector = create_connector(config.storage.connection, config.retry)
        # Get warn_stale_days from config if available
        warn_stale_days = None
        if config.lineage and config.lineage.query_history:
            warn_stale_days = config.lineage.query_history.warn_stale_days
        client = MetadataQueryClient(
            connector.engine,
            runs_table=config.storage.runs_table,
            results_table=config.storage.results_table,
            events_table="baselinr_events",
            warn_stale_days=warn_stale_days,
        )

        # Execute subcommand
        if args.lineage_command == "upstream":
            if args.column:
                # Column-level lineage
                lineage_data = client.query_column_lineage_upstream(
                    args.table,
                    args.column,
                    schema_name=args.schema,
                    max_depth=args.max_depth,
                )
            else:
                # Table-level lineage
                lineage_data = client.query_lineage_upstream(
                    args.table, schema_name=args.schema, max_depth=args.max_depth
                )

            if not lineage_data:
                if args.column:
                    safe_print(
                        f"No upstream column lineage found for "
                        f"{args.schema or ''}.{args.table}.{args.column}"
                    )
                else:
                    safe_print(f"No upstream lineage found for {args.schema or ''}.{args.table}")
                return 0

            if args.format == "json":
                output = json.dumps(lineage_data, indent=2, default=str)
                safe_print(output)
            else:
                from rich.table import Table as RichTable

                from .cli_output import get_console

                console = get_console()
                if console:
                    if args.column:
                        title = f"Upstream Column Lineage: {args.table}.{args.column}"
                    else:
                        title = f"Upstream Lineage: {args.table}"
                    table = RichTable(
                        title=title,
                        show_header=True,
                        header_style="bold cyan",
                    )
                    table.add_column("Schema", style="cyan")
                    table.add_column("Table", style="green")
                    if args.column:
                        table.add_column("Column", style="magenta")
                    table.add_column("Depth", justify="right", style="yellow")
                    table.add_column("Provider", style="dim")
                    table.add_column("Type", style="dim")
                    table.add_column("Confidence", justify="right", style="dim")
                    if args.column:
                        table.add_column("Transformation", style="dim")

                    for item in lineage_data:
                        row = [
                            item.get("schema", ""),
                            item.get("table", ""),
                        ]
                        if args.column:
                            row.append(item.get("column", ""))
                        row.extend(
                            [
                                str(item.get("depth", 0)),
                                item.get("provider", "unknown"),
                                item.get("lineage_type", ""),
                                f"{item.get('confidence_score', 1.0):.2f}",
                            ]
                        )
                        if args.column:
                            row.append(item.get("transformation_expression", "") or "")
                        table.add_row(*row)
                    safe_print()
                    safe_print(table)
                else:
                    # Fallback to plain text
                    if args.column:
                        output = f"\nUpstream Column Lineage for {args.table}.{args.column}:\n"
                    else:
                        output = f"\nUpstream Lineage for {args.table}:\n"
                    output += "=" * 80 + "\n"
                    for item in lineage_data:
                        if args.column:
                            output += (
                                f"  {item.get('schema', '')}.{item.get('table', '')}."
                                f"{item.get('column', '')} "
                            )
                        else:
                            output += f"  {item.get('schema', '')}.{item.get('table', '')} "
                        output += f"(depth: {item.get('depth', 0)}, "
                        output += f"provider: {item.get('provider', 'unknown')})\n"
                    safe_print(output)

            if args.output:
                with open(args.output, "w") as f:
                    if args.format == "json":
                        f.write(output)
                    else:
                        f.write(json.dumps(lineage_data, indent=2, default=str))
                logger.info(f"Results saved to: {args.output}")

        elif args.lineage_command == "downstream":
            if args.column:
                # Column-level lineage
                lineage_data = client.query_column_lineage_downstream(
                    args.table,
                    args.column,
                    schema_name=args.schema,
                    max_depth=args.max_depth,
                )
            else:
                # Table-level lineage
                lineage_data = client.query_lineage_downstream(
                    args.table, schema_name=args.schema, max_depth=args.max_depth
                )

            if not lineage_data:
                if args.column:
                    safe_print(
                        f"No downstream column lineage found for "
                        f"{args.schema or ''}.{args.table}.{args.column}"
                    )
                else:
                    safe_print(f"No downstream lineage found for {args.schema or ''}.{args.table}")
                return 0

            if args.format == "json":
                output = json.dumps(lineage_data, indent=2, default=str)
                safe_print(output)
            else:
                from rich.table import Table as RichTable

                from .cli_output import get_console

                console = get_console()
                if console:
                    if args.column:
                        title = f"Downstream Column Lineage: {args.table}.{args.column}"
                    else:
                        title = f"Downstream Lineage: {args.table}"
                    table = RichTable(
                        title=title,
                        show_header=True,
                        header_style="bold cyan",
                    )
                    table.add_column("Schema", style="cyan")
                    table.add_column("Table", style="green")
                    if args.column:
                        table.add_column("Column", style="magenta")
                    table.add_column("Depth", justify="right", style="yellow")
                    table.add_column("Provider", style="dim")
                    table.add_column("Type", style="dim")
                    table.add_column("Confidence", justify="right", style="dim")
                    if args.column:
                        table.add_column("Transformation", style="dim")

                    for item in lineage_data:
                        row = [
                            item.get("schema", ""),
                            item.get("table", ""),
                        ]
                        if args.column:
                            row.append(item.get("column", ""))
                        row.extend(
                            [
                                str(item.get("depth", 0)),
                                item.get("provider", "unknown"),
                                item.get("lineage_type", ""),
                                f"{item.get('confidence_score', 1.0):.2f}",
                            ]
                        )
                        if args.column:
                            row.append(item.get("transformation_expression", "") or "")
                        table.add_row(*row)
                    safe_print()
                    safe_print(table)
                else:
                    # Fallback to plain text
                    if args.column:
                        output = f"\nDownstream Column Lineage for {args.table}.{args.column}:\n"
                    else:
                        output = f"\nDownstream Lineage for {args.table}:\n"
                    output += "=" * 80 + "\n"
                    for item in lineage_data:
                        if args.column:
                            output += (
                                f"  {item.get('schema', '')}.{item.get('table', '')}."
                                f"{item.get('column', '')} "
                            )
                        else:
                            output += f"  {item.get('schema', '')}.{item.get('table', '')} "
                        output += f"(depth: {item.get('depth', 0)}, "
                        output += f"provider: {item.get('provider', 'unknown')})\n"
                    safe_print(output)

            if args.output:
                with open(args.output, "w") as f:
                    if args.format == "json":
                        f.write(output)
                    else:
                        f.write(json.dumps(lineage_data, indent=2, default=str))
                logger.info(f"Results saved to: {args.output}")

        elif args.lineage_command == "path":
            # Parse from/to tables (support schema.table format)
            from_parts = args.from_table.split(".", 1)
            from_table_name = from_parts[-1]
            from_schema = from_parts[0] if len(from_parts) == 2 else None

            to_parts = args.to_table.split(".", 1)
            to_table_name = to_parts[-1]
            to_schema = to_parts[0] if len(to_parts) == 2 else None

            if args.from_column and args.to_column:
                # Column-level lineage path
                path = client.query_column_lineage_path(
                    from_table_name,
                    args.from_column,
                    to_table_name,
                    args.to_column,
                    from_schema=from_schema,
                    to_schema=to_schema,
                    max_depth=args.max_depth,
                )
            else:
                # Table-level lineage path
                path = client.query_lineage_path(
                    from_table_name,
                    to_table_name,
                    from_schema=from_schema,
                    to_schema=to_schema,
                    max_depth=args.max_depth,
                )

            if not path:
                if args.from_column and args.to_column:
                    safe_print(
                        f"No column path found from {args.from_table}.{args.from_column} "
                        f"to {args.to_table}.{args.to_column}"
                    )
                else:
                    safe_print(f"No path found from {args.from_table} to {args.to_table}")
                return 0

            if args.format == "json":
                output = json.dumps(path, indent=2, default=str)
                safe_print(output)
            else:
                from rich.table import Table as RichTable

                from .cli_output import get_console

                console = get_console()
                if console:
                    if args.from_column and args.to_column:
                        title = (
                            f"Column Lineage Path: {args.from_table}.{args.from_column} → "
                            f"{args.to_table}.{args.to_column}"
                        )
                    else:
                        title = f"Lineage Path: {args.from_table} → {args.to_table}"
                    table = RichTable(
                        title=title,
                        show_header=True,
                        header_style="bold cyan",
                    )
                    table.add_column("Step", justify="right", style="yellow")
                    table.add_column("Schema", style="cyan")
                    table.add_column("Table", style="green")
                    if args.from_column and args.to_column:
                        table.add_column("Column", style="magenta")

                    for i, item in enumerate(path):
                        row = [
                            str(i + 1),
                            item.get("schema", ""),
                            item.get("table", ""),
                        ]
                        if args.from_column and args.to_column:
                            row.append(item.get("column", ""))
                        table.add_row(*row)
                    safe_print()
                    safe_print(table)
                else:
                    # Fallback to plain text
                    if args.from_column and args.to_column:
                        output = (
                            f"\nColumn Lineage Path from {args.from_table}.{args.from_column} "
                            f"to {args.to_table}.{args.to_column}:\n"
                        )
                    else:
                        output = f"\nLineage Path from {args.from_table} to {args.to_table}:\n"
                    output += "=" * 80 + "\n"
                    for i, item in enumerate(path):
                        output += f"  {i+1}. {item.get('schema', '')}.{item.get('table', '')}\n"
                    safe_print(output)

            if args.output:
                with open(args.output, "w") as f:
                    if args.format == "json":
                        f.write(output)
                    else:
                        f.write(json.dumps(path, indent=2, default=str))
                logger.info(f"Results saved to: {args.output}")

        elif args.lineage_command == "providers":
            try:
                from .connectors.factory import create_connector
                from .integrations.lineage import LineageProviderRegistry

                # Create source connector for registry
                source_connector = create_connector(config.source, config.retry)
                source_engine = source_connector.engine

                # Create registry with config and source engine
                registry = LineageProviderRegistry(config=config, source_engine=source_engine)
                available = registry.get_available_providers()
                all_providers = registry._providers

                if args.format == "json":
                    providers_data = {
                        "available": [p.get_provider_name() for p in available],
                        "all": [
                            {
                                "name": p.get_provider_name(),
                                "available": p.is_available(),
                            }
                            for p in all_providers
                        ],
                    }
                    output = json.dumps(providers_data, indent=2)
                    safe_print(output)
                else:
                    from rich.table import Table as RichTable

                    from .cli_output import get_console

                    console = get_console()
                    if console:
                        table = RichTable(
                            title="Lineage Providers",
                            show_header=True,
                            header_style="bold cyan",
                        )
                        table.add_column("Provider", style="cyan")
                        table.add_column("Status", justify="center")

                        for provider in all_providers:
                            name = provider.get_provider_name()
                            is_avail = provider.is_available()
                            status = (
                                "[green]Available[/green]" if is_avail else "[red]Unavailable[/red]"
                            )
                            table.add_row(name, status)
                        safe_print()
                        safe_print(table)
                    else:
                        # Fallback to plain text
                        output = "\nLineage Providers:\n"
                        output += "=" * 80 + "\n"
                        for provider in all_providers:
                            name = provider.get_provider_name()
                            is_avail = provider.is_available()
                            status = "Available" if is_avail else "Unavailable"
                            output += f"  {name}: {status}\n"
                        safe_print(output)

            except Exception as e:
                logger.warning(f"Could not list providers: {e}")
                safe_print(f"Could not list lineage providers: {e}")

        elif args.lineage_command == "sync":
            from .connectors.factory import create_connector
            from .integrations.lineage import LineageProviderRegistry
            from .storage.writer import ResultWriter

            # Create source connector for registry
            source_connector = create_connector(config.source, config.retry)
            source_engine = source_connector.engine

            # Create registry with config
            # Sync tracker is created automatically by registry
            registry = LineageProviderRegistry(config=config, source_engine=source_engine)

            # Get query history providers
            all_providers = registry._providers
            provider_names = [
                p.get_provider_name() if hasattr(p, "get_provider_name") else type(p).__name__
                for p in all_providers
            ]
            logger.debug(f"All registered providers: {provider_names}")
            query_history_providers = [
                p
                for p in all_providers
                if hasattr(p, "get_provider_name")
                and p.get_provider_name().endswith("_query_history")
            ]

            if not query_history_providers:
                safe_print("No query history providers found")
                provider_names = [
                    p.get_provider_name() if hasattr(p, "get_provider_name") else type(p).__name__
                    for p in all_providers
                ]
                safe_print(f"Available providers: {provider_names}")
                return 0

            # Filter by provider name if specified
            if args.provider:
                query_history_providers = [
                    p for p in query_history_providers if p.get_provider_name() == args.provider
                ]
                if not query_history_providers:
                    safe_print(f"Provider '{args.provider}' not found")
                    return 1

            # Override lookback_days if specified
            if args.lookback_days:
                for provider in query_history_providers:
                    if hasattr(provider, "lookback_days"):
                        provider.lookback_days = args.lookback_days

            # Force resync if requested
            if args.force:
                for provider in query_history_providers:
                    if hasattr(provider, "sync_tracker") and provider.sync_tracker:
                        # Clear last sync by setting it to None (will trigger full sync)
                        provider.sync_tracker.update_sync(
                            provider.get_provider_name(),
                            datetime(1970, 1, 1),  # Very old timestamp
                            0,
                            0,
                        )

            # Create writer for storing lineage
            writer = ResultWriter(
                config.storage, config.retry, baselinr_config=config, event_bus=None
            )

            total_edges = 0

            for provider in query_history_providers:
                if not provider.is_available():
                    safe_print(
                        f"Provider {provider.get_provider_name()} is not available, skipping"
                    )
                    continue

                safe_print(f"Syncing lineage from {provider.get_provider_name()}...")

                try:
                    # Get all lineage
                    all_lineage = provider.get_all_lineage()

                    if args.dry_run:
                        edge_count = sum(len(edges) for edges in all_lineage.values())
                        safe_print(
                            f"  Would extract {edge_count} edges from {len(all_lineage)} tables"
                        )
                        continue

                    # Write lineage
                    all_edges = []
                    for edges in all_lineage.values():
                        all_edges.extend(edges)

                    if all_edges:
                        writer.write_lineage(all_edges)
                        total_edges += len(all_edges)
                        safe_print(f"  Extracted {len(all_edges)} lineage edges")

                except Exception as e:
                    logger.error(f"Error syncing {provider.get_provider_name()}: {e}")
                    safe_print(f"  Error: {e}")

            if not args.dry_run:
                safe_print(f"\nSync complete: {total_edges} edges extracted")

        elif args.lineage_command == "show":
            # Phase 3: Show lineage with impact scoring
            from .smart_selection.lineage import ImpactScorer, LineageAdapter, LineageGraph

            # Create lineage adapter
            adapter = LineageAdapter(
                engine=connector.engine,
                lineage_table="baselinr_lineage",
                cache_ttl_hours=24,
                max_depth=10,
            )

            # Build graph and compute impact score
            graph = LineageGraph.build_from_adapter(adapter)
            scorer = ImpactScorer(graph)

            node = graph.get_node(args.table, args.schema)
            if not node:
                safe_print(f"Table {args.schema or ''}.{args.table} not found in lineage graph")
                return 0

            impact_score = scorer.score_table(args.table, args.schema)

            if args.format == "json":
                import json

                result = {
                    "table": args.table,
                    "schema": args.schema or "",
                    "node": node.to_dict() if node else {},
                    "impact_score": impact_score.to_dict() if impact_score else {},
                    "upstream_tables": node.upstream[:20] if node else [],
                    "downstream_tables": node.downstream[:20] if node else [],
                }
                output = json.dumps(result, indent=2, default=str)
                safe_print(output)
            else:
                from rich.table import Table as RichTable

                from .cli_output import get_console

                console = get_console()
                if console:
                    # Node info
                    table_ref = f"{args.schema}.{args.table}" if args.schema else args.table
                    safe_print()
                    safe_print(f"[bold cyan]Lineage for {table_ref}[/bold cyan]")
                    safe_print()

                    # Position and type
                    safe_print(f"  Node Type: {node.node_type}")
                    safe_print(
                        f"  Position: {impact_score.position if impact_score else 'unknown'}"
                    )
                    safe_print(f"  Depth: {node.depth}")
                    safe_print(f"  Critical Path: {'Yes' if node.critical_path_member else 'No'}")
                    safe_print()

                    # Impact score
                    if impact_score:
                        safe_print("[bold]Impact Score:[/bold]")
                        safe_print(f"  Total Score: {impact_score.total_score:.4f}")
                        safe_print(f"  Downstream Score: {impact_score.downstream_score:.4f}")
                        safe_print(f"  Depth Score: {impact_score.depth_score:.4f}")
                        safe_print(f"  Criticality Score: {impact_score.criticality_score:.4f}")
                        safe_print(f"  Fanout Score: {impact_score.fanout_score:.4f}")
                        safe_print()

                        # Blast radius
                        br = impact_score.blast_radius
                        safe_print("[bold]Blast Radius:[/bold]")
                        safe_print(f"  Immediate Downstream: {br.immediate_downstream}")
                        safe_print(f"  Total Affected: {br.total_affected}")
                        safe_print(f"  Critical Assets: {br.critical_assets_affected}")
                        safe_print(f"  User Impact: {br.estimated_user_impact}")
                        safe_print()

                        # Reasoning
                        safe_print("[bold]Reasoning:[/bold]")
                        for reason in impact_score.reasoning:
                            safe_print(f"  • {reason}")
                        safe_print()

                    # Dependencies
                    if node.upstream:
                        safe_print(f"[bold]Upstream Dependencies ({len(node.upstream)}):[/bold]")
                        for dep in node.upstream[:10]:
                            safe_print(f"  ← {dep}")
                        if len(node.upstream) > 10:
                            safe_print(f"  ... and {len(node.upstream) - 10} more")
                        safe_print()

                    if node.downstream:
                        safe_print(
                            f"[bold]Downstream Dependencies ({len(node.downstream)}):[/bold]"
                        )
                        for dep in node.downstream[:10]:
                            safe_print(f"  → {dep}")
                        if len(node.downstream) > 10:
                            safe_print(f"  ... and {len(node.downstream) - 10} more")
                        safe_print()
                else:
                    # Plain text fallback
                    safe_print(f"\nLineage for {args.schema or ''}.{args.table}:")
                    safe_print("=" * 60)
                    if node:
                        safe_print(f"  Type: {node.node_type}")
                        safe_print(f"  Depth: {node.depth}")
                        safe_print(f"  Upstream: {node.upstream_count}")
                        safe_print(f"  Downstream: {node.downstream_count}")
                    if impact_score:
                        safe_print(f"  Impact Score: {impact_score.total_score:.4f}")
                        safe_print(
                            f"  User Impact: {impact_score.blast_radius.estimated_user_impact}"
                        )

            if args.output:
                with open(args.output, "w") as f:
                    import json

                    result = {
                        "table": args.table,
                        "schema": args.schema or "",
                        "node": node.to_dict() if node else {},
                        "impact_score": impact_score.to_dict() if impact_score else {},
                    }
                    f.write(json.dumps(result, indent=2, default=str))
                logger.info(f"Results saved to: {args.output}")

        elif args.lineage_command == "impact":
            # Phase 3: Show blast radius for a table
            from .smart_selection.lineage import ImpactScorer, LineageAdapter, LineageGraph

            adapter = LineageAdapter(
                engine=connector.engine,
                lineage_table="baselinr_lineage",
            )

            graph = LineageGraph.build_from_adapter(adapter)
            scorer = ImpactScorer(graph)
            impact_score = scorer.score_table(args.table, args.schema)

            if not impact_score:
                safe_print(f"Table {args.schema or ''}.{args.table} not found in lineage graph")
                return 0

            if args.format == "json":
                import json

                output = json.dumps(impact_score.to_dict(), indent=2, default=str)
                safe_print(output)
            else:
                from .cli_output import get_console

                console = get_console()
                br = impact_score.blast_radius

                if console:
                    safe_print()
                    table_ref = f"{args.schema}.{args.table}" if args.schema else args.table
                    safe_print(f"[bold cyan]Blast Radius for {table_ref}[/bold cyan]")
                    safe_print()
                    safe_print(f"  [bold]User Impact Level:[/bold] {br.estimated_user_impact}")
                    safe_print()
                    safe_print(f"  Immediate Downstream: {br.immediate_downstream} tables")
                    safe_print(f"  Total Affected: {br.total_affected} tables")
                    safe_print(f"  Critical Assets Affected: {br.critical_assets_affected}")
                    safe_print()

                    if br.affected_exposures:
                        safe_print("[bold]Affected Exposures:[/bold]")
                        for exp in br.affected_exposures[:10]:
                            safe_print(f"  • {exp}")
                        if len(br.affected_exposures) > 10:
                            safe_print(f"  ... and {len(br.affected_exposures) - 10} more")
                        safe_print()

                    if br.affected_tables:
                        safe_print(f"[bold]Affected Tables ({len(br.affected_tables)}):[/bold]")
                        for t in br.affected_tables[:15]:
                            safe_print(f"  • {t}")
                        if len(br.affected_tables) > 15:
                            safe_print(f"  ... and {len(br.affected_tables) - 15} more")
                        safe_print()
                else:
                    safe_print(f"\nBlast Radius for {args.schema or ''}.{args.table}:")
                    safe_print("=" * 60)
                    safe_print(f"  User Impact: {br.estimated_user_impact}")
                    safe_print(f"  Immediate Downstream: {br.immediate_downstream}")
                    safe_print(f"  Total Affected: {br.total_affected}")
                    safe_print(f"  Critical Assets: {br.critical_assets_affected}")

            if args.output:
                with open(args.output, "w") as f:
                    import json

                    f.write(json.dumps(impact_score.to_dict(), indent=2, default=str))
                logger.info(f"Results saved to: {args.output}")

        elif args.lineage_command == "validate":
            # Phase 3: Validate lineage availability and graph structure
            from .smart_selection.lineage import LineageAdapter, LineageGraph

            adapter = LineageAdapter(
                engine=connector.engine,
                lineage_table="baselinr_lineage",
            )

            # Check if lineage data exists
            stats = adapter.get_lineage_stats()

            if stats.get("total_edges", 0) == 0:
                safe_print("❌ No lineage data found in the database.")
                safe_print("   Run 'baselinr lineage sync' to populate lineage data.")
                return 1

            # Build graph
            graph = LineageGraph.build_from_adapter(adapter)
            graph_stats = graph.get_stats()

            if args.format == "json":
                import json

                result = {
                    "valid": True,
                    "lineage_stats": stats,
                    "graph_stats": graph_stats,
                }
                output = json.dumps(result, indent=2, default=str)
                safe_print(output)
            else:
                from .cli_output import get_console

                console = get_console()
                if console:
                    safe_print()
                    safe_print("[bold green]✓ Lineage Validation Passed[/bold green]")
                    safe_print()
                    safe_print("[bold]Lineage Data:[/bold]")
                    safe_print(f"  Total Edges: {stats.get('total_edges', 0)}")
                    safe_print(f"  Total Tables: {stats.get('total_tables', 0)}")
                    if stats.get("edges_by_provider"):
                        safe_print("  Edges by Provider:")
                        for provider, count in stats["edges_by_provider"].items():
                            safe_print(f"    - {provider}: {count}")
                    safe_print()

                    safe_print("[bold]Graph Structure:[/bold]")
                    safe_print(f"  Total Nodes: {graph_stats.get('total_nodes', 0)}")
                    safe_print(f"  Root Tables (Sources): {graph_stats.get('total_roots', 0)}")
                    safe_print(f"  Leaf Tables (Outputs): {graph_stats.get('total_leaves', 0)}")
                    safe_print(f"  Orphaned Tables: {graph_stats.get('total_orphans', 0)}")
                    safe_print(f"  Max Depth: {graph_stats.get('max_depth', 0)}")
                    safe_print(f"  Critical Paths: {graph_stats.get('critical_paths_count', 0)}")

                    if graph_stats.get("node_type_distribution"):
                        safe_print()
                        safe_print("[bold]Node Type Distribution:[/bold]")
                        for node_type, count in graph_stats["node_type_distribution"].items():
                            safe_print(f"  - {node_type}: {count}")
                    safe_print()
                else:
                    safe_print("\n✓ Lineage Validation Passed")
                    safe_print("=" * 60)
                    safe_print(f"  Total Edges: {stats.get('total_edges', 0)}")
                    safe_print(f"  Total Nodes: {graph_stats.get('total_nodes', 0)}")
                    safe_print(f"  Roots: {graph_stats.get('total_roots', 0)}")
                    safe_print(f"  Leaves: {graph_stats.get('total_leaves', 0)}")
                    safe_print(f"  Max Depth: {graph_stats.get('max_depth', 0)}")

        elif args.lineage_command == "refresh-cache":
            # Phase 3: Refresh lineage cache
            from .smart_selection.lineage import LineageAdapter

            adapter = LineageAdapter(
                engine=connector.engine,
                lineage_table="baselinr_lineage",
            )
            adapter.refresh_cache()
            safe_print("✓ Lineage cache refreshed")

        elif args.lineage_command == "cleanup":
            from datetime import datetime, timedelta

            from sqlalchemy import text

            from .connectors.factory import create_connector

            # Get config
            query_history_config = (
                config.lineage.query_history
                if config.lineage and config.lineage.query_history
                else None
            )

            if not query_history_config:
                safe_print("Query history configuration not found")
                return 1

            expiration_days = args.expiration_days or query_history_config.edge_expiration_days

            if expiration_days is None:
                safe_print(
                    "No expiration_days configured. "
                    "Set edge_expiration_days in config or use --expiration-days"
                )
                return 1

            # Create storage connector
            storage_connector = create_connector(config.storage.connection, config.retry)
            engine = storage_connector.engine

            # Determine provider filter
            provider_filter = ""
            if args.provider:
                provider_filter = f"AND provider = '{args.provider}'"
            else:
                # Clean up all query history providers
                provider_filter = "AND provider LIKE '%_query_history'"

            # Calculate cutoff timestamp
            cutoff_timestamp = datetime.utcnow() - timedelta(days=expiration_days)

            with engine.connect() as conn:
                # Count stale edges
                count_sql = text(
                    f"""
                    SELECT COUNT(*)
                    FROM baselinr_lineage
                    WHERE last_seen_at < :cutoff_timestamp
                      {provider_filter}
                """
                )
                count_result = conn.execute(count_sql, {"cutoff_timestamp": cutoff_timestamp})
                stale_count = count_result.scalar()

                if stale_count == 0:
                    safe_print("No stale edges found")
                    return 0

                if args.dry_run:
                    safe_print(
                        f"Would delete {stale_count} stale edges "
                        f"(older than {expiration_days} days)"
                    )
                    return 0

                # Delete stale edges
                delete_sql = text(
                    f"""
                    DELETE FROM baselinr_lineage
                    WHERE last_seen_at < :cutoff_timestamp
                      {provider_filter}
                """
                )
                result = conn.execute(delete_sql, {"cutoff_timestamp": cutoff_timestamp})
                deleted_count = result.rowcount
                conn.commit()

                safe_print(f"Cleaned up {deleted_count} stale edges")

        return 0

    except Exception as e:
        logger.error(f"Lineage command failed: {e}", exc_info=True)
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


def chat_command(args):
    """Execute chat command - interactive data quality investigation."""
    try:
        from .chat.cli import run_chat_command

        return run_chat_command(args)
    except KeyboardInterrupt:
        logger.info("Chat command interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Chat command failed: {e}", exc_info=True)
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

    # Initialize quality score storage if enabled
    quality_storage = None
    if config.quality_scoring and config.quality_scoring.enabled:
        try:
            from .quality.storage import QualityScoreStorage

            storage_connector = create_connector(config.storage.connection, config.retry)
            quality_storage = QualityScoreStorage(
                engine=storage_connector.engine,
                scores_table="baselinr_quality_scores",
            )
        except Exception as e:
            logger.debug(f"Could not initialize quality score storage: {e}")

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

        # Fetch quality score if available
        quality_score = None
        quality_status = None
        if quality_storage:
            try:
                latest_score = quality_storage.get_latest_score(run.dataset_name, run.schema_name)
                if latest_score:
                    quality_score = latest_score.overall_score
                    quality_status = latest_score.status
            except Exception as e:
                logger.debug(f"Could not fetch quality score for {run.dataset_name}: {e}")

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
                "quality_score": quality_score,
                "quality_status": quality_status,
                # Keep legacy status_indicator for text/JSON formats
                "status_indicator": (
                    "healthy"
                    if not has_drift and anomalies_count == 0
                    else ("error" if has_drift and severity == "high" else "warning")
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

        # Initialize quality score storage if enabled
        quality_storage = None
        if config.quality_scoring and config.quality_scoring.enabled:
            try:
                from .quality.storage import QualityScoreStorage

                storage_connector = create_connector(config.storage.connection, config.retry)
                quality_storage = QualityScoreStorage(
                    engine=storage_connector.engine,
                    scores_table="baselinr_quality_scores",
                )
            except Exception as e:
                logger.debug(f"Could not initialize quality score storage: {e}")

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

                # Fetch quality score if available
                quality_score = None
                quality_status = None
                if quality_storage:
                    try:
                        latest_score = quality_storage.get_latest_score(
                            run.dataset_name, run.schema_name
                        )
                        if latest_score:
                            quality_score = latest_score.overall_score
                            quality_status = latest_score.status
                    except Exception as e:
                        logger.debug(f"Could not fetch quality score for {run.dataset_name}: {e}")

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
                        "quality_score": quality_score,
                        "quality_status": quality_status,
                        "drift_severity": severity,
                        # Keep legacy status_indicator for text/JSON formats
                        "status_indicator": (
                            "healthy"
                            if not has_drift and anomalies_count == 0
                            else ("error" if has_drift and severity == "high" else "warning")
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
                            status = run.get("status_indicator", "healthy")

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
                print("\n[WARNING] Schema version not initialized")
                print("Run: baselinr migrate apply --target 1")
            elif current < CURRENT_SCHEMA_VERSION:
                print(
                    f"\n[WARNING] Database schema is behind "
                    f"(v{current} < v{CURRENT_SCHEMA_VERSION})"
                )
                print(f"Run: baselinr migrate apply --target {CURRENT_SCHEMA_VERSION}")
            elif current > CURRENT_SCHEMA_VERSION:
                print(
                    f"\n[ERROR] Database schema is ahead "
                    f"(v{current} > v{CURRENT_SCHEMA_VERSION})"
                )
                print("Update Baselinr package to match database version")
            else:
                print("\n[SUCCESS] Schema version is up to date")

        elif args.migrate_command == "apply":
            target = args.target
            dry_run = args.dry_run

            if dry_run:
                print("[DRY RUN] No changes will be applied\n")

            success = manager.migrate_to(target, dry_run=dry_run)

            if success:
                if not dry_run:
                    print(f"\n[SUCCESS] Successfully migrated to version {target}")
                return 0
            else:
                print("\n[ERROR] Migration failed")
                return 1

        elif args.migrate_command == "validate":
            print("Validating schema integrity...\n")
            results = manager.validate_schema()

            print(f"Schema Version: {results['version']}")
            print(f"Valid: {'[SUCCESS] Yes' if results['valid'] else '[ERROR] No'}\n")

            if results["errors"]:
                print("Errors:")
                for error in results["errors"]:
                    print(f"  [ERROR] {error}")
                print()

            if results["warnings"]:
                print("Warnings:")
                for warning in results["warnings"]:
                    print(f"  [WARNING] {warning}")
                print()

            return 0 if results["valid"] else 1

        return 0

    except Exception as e:
        logger.error(f"Migration command failed: {e}", exc_info=True)
        print(f"\n[ERROR] {e}")
        return 1


def recommend_command(args):
    """Execute recommend command to generate smart table and column recommendations."""
    import json

    from .cli_output import safe_print
    from .connectors.factory import create_connector
    from .smart_selection import RecommendationEngine, SmartSelectionConfig

    log_event(
        logger,
        "command_started",
        f"Loading configuration from: {args.config}",
        metadata={"config_path": args.config, "command": "recommend"},
    )

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)
        log_event(
            logger,
            "config_loaded",
            f"Configuration loaded for environment: {config.environment}",
            metadata={"environment": config.environment},
        )

        # Get smart selection config or use defaults
        if hasattr(config, "smart_selection") and config.smart_selection:
            # Handle if it's a dict (from YAML) vs SmartSelectionConfig
            if isinstance(config.smart_selection, dict):
                smart_config = SmartSelectionConfig(**config.smart_selection)
            else:
                smart_config = config.smart_selection
        else:
            # Use defaults
            smart_config = SmartSelectionConfig(
                enabled=True,
                mode="recommend",
            )
            logger.info("No smart_selection config found, using defaults")

        # Override output file if specified
        output_file = args.output or smart_config.recommendations.output_file

        # Determine if we're doing column recommendations
        include_columns = getattr(args, "columns", False)
        specific_table = getattr(args, "table", None)

        # Create database connector
        connector = create_connector(config.source, config.retry, config.execution)

        # Create storage connector if storage config exists (for column profiling data)
        storage_engine = None
        if hasattr(config, "storage") and config.storage:
            try:
                from .connectors.factory import create_connector as create_storage_connector

                storage_connector = create_storage_connector(
                    config.storage.connection, config.retry, config.execution
                )
                storage_engine = storage_connector.engine
            except Exception as e:
                logger.warning(f"Could not create storage connector: {e}")

        # Check for lineage options
        with_lineage = getattr(args, "with_lineage", False)
        explain_lineage = getattr(args, "explain_lineage", False)

        if include_columns:
            safe_print("\n📊 Generating smart table and column recommendations...")
        else:
            safe_print("\n📊 Generating smart table recommendations...")

        safe_print(f"   Database: {config.source.database} ({config.source.type})")
        if args.schema:
            safe_print(f"   Schema: {args.schema}")
        if specific_table:
            safe_print(f"   Table: {specific_table}")
        safe_print(f"   Lookback period: {smart_config.criteria.lookback_days} days")
        if include_columns:
            safe_print("   Column analysis: enabled")
        if with_lineage:
            safe_print("   Lineage-aware scoring: enabled")
        safe_print("")

        # Handle explain-lineage mode for specific table
        if explain_lineage and specific_table and storage_engine:
            from .smart_selection.lineage import ImpactScorer, LineageAdapter, LineageGraph

            safe_print(f"📊 Lineage explanation for {args.schema or 'default'}.{specific_table}...")
            safe_print("")

            adapter = LineageAdapter(
                engine=storage_engine,
                lineage_table="baselinr_lineage",
            )

            # Check if lineage data exists
            if not adapter.has_lineage_data(specific_table, args.schema):
                safe_print("⚠️  No lineage data found for this table.")
                safe_print("   Run 'baselinr lineage sync' to populate lineage data.")
                return 0

            graph = LineageGraph.build_from_adapter(adapter)
            scorer = ImpactScorer(graph)
            impact_score = scorer.score_table(specific_table, args.schema)

            if impact_score:
                safe_print(f"[bold]Impact Score:[/bold] {impact_score.total_score:.4f}")
                safe_print(f"[bold]Position:[/bold] {impact_score.position}")
                safe_print(f"[bold]Node Type:[/bold] {impact_score.node_type}")
                is_critical = "Yes" if impact_score.is_critical_path else "No"
                safe_print(f"[bold]Critical Path:[/bold] {is_critical}")
                safe_print("")

                safe_print("[bold]Score Components:[/bold]")
                safe_print(f"  Downstream: {impact_score.downstream_score:.4f}")
                safe_print(f"  Depth: {impact_score.depth_score:.4f}")
                safe_print(f"  Criticality: {impact_score.criticality_score:.4f}")
                safe_print(f"  Fanout: {impact_score.fanout_score:.4f}")
                safe_print("")

                br = impact_score.blast_radius
                safe_print("[bold]Blast Radius:[/bold]")
                safe_print(f"  Immediate Downstream: {br.immediate_downstream}")
                safe_print(f"  Total Affected: {br.total_affected}")
                safe_print(f"  Critical Assets: {br.critical_assets_affected}")
                safe_print(f"  User Impact: {br.estimated_user_impact}")
                safe_print("")

                safe_print("[bold]Reasoning:[/bold]")
                for reason in impact_score.reasoning:
                    safe_print(f"  • {reason}")
                safe_print("")

                # Show check adjustments
                check_adjustments = smart_config.lineage.check_adjustments
                if impact_score.position == "root":
                    adj = check_adjustments.root_tables
                    if adj.prioritize_checks:
                        safe_print("[bold]Recommended Check Priority (Root Table):[/bold]")
                        for check in adj.prioritize_checks:
                            safe_print(f"  • {check} (severity: {adj.severity or 'default'})")
                elif impact_score.total_score >= 0.7:
                    adj = check_adjustments.high_impact
                    safe_print("[bold]High Impact Table Adjustments:[/bold]")
                    if adj.min_confidence_threshold:
                        safe_print(f"  Min confidence threshold: {adj.min_confidence_threshold}")
                    if adj.check_frequency:
                        safe_print(f"  Check frequency: {adj.check_frequency}")
                elif impact_score.position == "leaf":
                    adj = check_adjustments.leaf_tables
                    safe_print("[bold]Leaf Table Adjustments:[/bold]")
                    if adj.min_confidence_threshold:
                        safe_print(f"  Min confidence threshold: {adj.min_confidence_threshold}")
                    if adj.check_frequency:
                        safe_print(f"  Check frequency: {adj.check_frequency}")
            else:
                safe_print("❌ Could not compute impact score for this table")

            return 0

        # Create recommendation engine with storage engine
        engine = RecommendationEngine(
            connection_config=config.source,
            smart_config=smart_config,
            storage_engine=storage_engine,
        )

        # Handle single table column recommendations
        if specific_table:
            safe_print(f"Analyzing columns in {args.schema or 'default'}.{specific_table}...")
            col_recs = engine.generate_column_recommendations(
                engine=connector.engine,
                table_name=specific_table,
                schema=args.schema,
            )

            safe_print(f"✅ Found {len(col_recs)} column check recommendations")
            safe_print("")

            if args.explain and col_recs:
                _display_column_recommendations(col_recs, safe_print)

            # Save to file
            if args.format == "yaml":
                import yaml as yaml_lib  # type: ignore[import-untyped]

                with open(output_file, "w") as f:
                    table_ref = f"{args.schema or 'default'}.{specific_table}"
                    f.write(f"# Column Recommendations for {table_ref}\n")
                    f.write(f"# Generated: {__import__('datetime').datetime.now().isoformat()}\n\n")
                    yaml_lib.dump(
                        {"column_recommendations": [r.to_dict() for r in col_recs]},
                        f,
                        default_flow_style=False,
                        sort_keys=False,
                    )
                safe_print(f"💾 Saved recommendations to: {output_file}")

            return 0

        # Get existing tables to avoid duplicates
        existing_tables = config.profiling.tables if config.profiling else []

        # Generate recommendations
        report = engine.generate_recommendations(
            engine=connector.engine,
            schema=args.schema,
            existing_tables=existing_tables,
            include_columns=include_columns,
        )

        # Enhance with lineage scoring if enabled
        lineage_stats = None
        if with_lineage and storage_engine:
            try:
                from .smart_selection.lineage import ImpactScorer, LineageAdapter, LineageGraph

                safe_print("📊 Adding lineage-aware scoring...")
                adapter = LineageAdapter(
                    engine=storage_engine,
                    lineage_table="baselinr_lineage",
                )
                lineage_stats = adapter.get_lineage_stats()

                if lineage_stats.get("total_edges", 0) > 0:
                    graph = LineageGraph.build_from_adapter(adapter)
                    scorer = ImpactScorer(graph)

                    # Enhance each recommendation with lineage data
                    lineage_weight = smart_config.lineage.lineage_weight

                    for rec in report.recommended_tables:
                        impact_score = scorer.score_table(rec.table, rec.schema)
                        if impact_score:
                            # Store lineage info
                            rec.lineage_score = impact_score.total_score
                            rec.lineage_context = {
                                "node_type": impact_score.node_type,
                                "position": impact_score.position,
                                "is_critical_path": impact_score.is_critical_path,
                                "downstream_dependencies": {
                                    "immediate": impact_score.blast_radius.immediate_downstream,
                                    "total": impact_score.blast_radius.total_affected,
                                },
                                "blast_radius": {
                                    "affected_tables": (impact_score.blast_radius.total_affected),
                                    "affected_exposures": len(
                                        impact_score.blast_radius.affected_exposures
                                    ),
                                    "critical_dashboards": (
                                        impact_score.blast_radius.affected_exposures[:5]
                                    ),
                                    "estimated_user_impact": (
                                        impact_score.blast_radius.estimated_user_impact
                                    ),
                                },
                                "reasoning": impact_score.reasoning,
                            }

                            # Recalculate score with lineage weight
                            usage_weight = 1.0 - lineage_weight
                            usage_score = rec.score / 100.0 if rec.score else 0.0
                            combined = (
                                usage_weight * usage_score
                                + lineage_weight * impact_score.total_score
                            )
                            rec.score = combined * 100.0

                            # Add lineage-based reasons
                            rec.reasons.extend(impact_score.reasoning)

                    # Re-sort by new scores
                    report.recommended_tables.sort(key=lambda r: r.score, reverse=True)

                    safe_print(
                        f"   Lineage graph: {lineage_stats.get('total_tables', 0)} tables, "
                        f"{lineage_stats.get('total_edges', 0)} dependencies"
                    )
                else:
                    safe_print("   ⚠️  No lineage data found - scoring based on usage only")
            except Exception as e:
                logger.warning(f"Could not enhance with lineage scoring: {e}")
                safe_print(f"   ⚠️  Lineage scoring unavailable: {e}")

        safe_print("")

        # Display summary
        safe_print("✅ Analysis complete!")
        safe_print(f"   Tables analyzed: {report.total_tables_analyzed}")
        safe_print(f"   Recommended: {report.total_recommended}")
        safe_print(f"   Excluded: {report.total_excluded}")

        if include_columns and report.total_columns_analyzed > 0:
            safe_print("")
            safe_print(f"   Columns analyzed: {report.total_columns_analyzed}")
            safe_print(f"   Column checks recommended: {report.total_column_checks_recommended}")
            if report.column_confidence_distribution:
                high = report.column_confidence_distribution.get("high (0.8+)", 0)
                med = report.column_confidence_distribution.get("medium (0.5-0.8)", 0)
                low = report.column_confidence_distribution.get("low (<0.5)", 0)
                safe_print(f"   Column confidence: {high} high, {med} medium, {low} low")

        safe_print("")

        # Show table confidence distribution
        if report.confidence_distribution:
            safe_print("Table confidence distribution:")
            for level, count in report.confidence_distribution.items():
                if count > 0:
                    safe_print(f"   {level}: {count} tables")
            safe_print("")

        # Show recommendations if --explain flag
        if args.explain and report.recommended_tables:
            safe_print("Top recommendations:")
            safe_print("")

            for i, rec in enumerate(report.recommended_tables[:10], 1):
                safe_print(
                    f"{i}. {rec.schema}.{rec.table} "
                    f"(confidence: {rec.confidence:.2f}, score: {rec.score:.1f})"
                )

                if rec.reasons:
                    for reason in rec.reasons:
                        safe_print(f"   • {reason}")

                if rec.suggested_checks:
                    safe_print(f"   Suggested checks: {', '.join(rec.suggested_checks)}")

                if rec.warnings:
                    for warning in rec.warnings:
                        safe_print(f"   ⚠️  {warning}")

                # Show column recommendations if available
                if include_columns and rec.column_recommendations:
                    safe_print("")
                    safe_print(
                        f"   Column recommendations ({len(rec.column_recommendations)} columns):"
                    )
                    for col_rec in rec.column_recommendations[:5]:
                        checks = [c["type"] for c in col_rec.suggested_checks[:3]]
                        safe_print(
                            f"      • {col_rec.column} ({col_rec.data_type}): "
                            f"{', '.join(checks)} (conf: {col_rec.confidence:.2f})"
                        )
                    if len(rec.column_recommendations) > 5:
                        safe_print(
                            f"      ... and {len(rec.column_recommendations) - 5} more columns"
                        )

                safe_print("")

            if len(report.recommended_tables) > 10:
                safe_print(
                    f"... and {len(report.recommended_tables) - 10} more "
                    "(see output file for full list)"
                )
                safe_print("")

        # Save to file
        if args.format == "yaml":
            engine.save_recommendations(report, output_file)
            safe_print(f"💾 Saved recommendations to: {output_file}")
        elif args.format == "json":
            json_file = output_file.replace(".yaml", ".json").replace(".yml", ".json")
            with open(json_file, "w") as f:
                json.dump(report.to_yaml_dict(), f, indent=2, default=str)
            safe_print(f"💾 Saved recommendations to: {json_file}")

        # Handle --apply flag
        if args.apply:
            safe_print("")
            safe_print("⚠️  Apply mode: This will modify your configuration file!")
            safe_print(f"   {len(report.recommended_tables)} tables will be added to {args.config}")
            if include_columns:
                safe_print(
                    f"   {report.total_column_checks_recommended} column checks will be configured"
                )
            safe_print("")

            response = input("Do you want to continue? [y/N]: ")
            if response.lower() in ["y", "yes"]:
                _apply_recommendations(args.config, report, config, include_columns=include_columns)
                safe_print("✅ Configuration updated successfully!")
            else:
                safe_print("❌ Apply cancelled.")

        # Dry run mode
        if getattr(args, "dry_run", False):
            safe_print("")
            safe_print("🔍 Dry run mode - no changes applied")
            safe_print("   The above recommendations would be applied with --apply")

        # Success message
        safe_print("")
        safe_print("✨ Next steps:")
        safe_print(f"   1. Review recommendations in: {output_file}")
        if include_columns:
            safe_print(
                f"   2. Apply with: baselinr recommend --columns --config {args.config} --apply"
            )
        else:
            safe_print(f"   2. Apply with: baselinr recommend --config {args.config} --apply")
            safe_print(
                f"   3. Add column checks: baselinr recommend --columns --config {args.config}"
            )
        safe_print("   4. Or manually add tables to your config file")

        log_event(
            logger,
            "command_completed",
            "Recommend command completed successfully",
            metadata={
                "recommended_count": report.total_recommended,
                "excluded_count": report.total_excluded,
                "column_checks_count": report.total_column_checks_recommended,
            },
        )

        return 0

    except Exception as e:
        log_event(
            logger,
            "command_failed",
            f"Recommend command failed: {e}",
            level="error",
            metadata={"error": str(e), "error_type": type(e).__name__},
        )
        safe_print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


def _display_column_recommendations(col_recs, safe_print):
    """Display column recommendations in a readable format."""
    high_conf = [r for r in col_recs if r.confidence >= 0.8]
    medium_conf = [r for r in col_recs if 0.5 <= r.confidence < 0.8]
    low_conf = [r for r in col_recs if r.confidence < 0.5]

    if high_conf:
        safe_print("HIGH CONFIDENCE RECOMMENDATIONS:")
        safe_print("")
        for rec in high_conf:
            safe_print(f"✓ {rec.column} ({rec.data_type})")
            for check in rec.suggested_checks:
                safe_print(f"  → {check['type']} (confidence: {check.get('confidence', 'N/A')})")
                if check.get("config"):
                    for key, val in check["config"].items():
                        if key != "note":
                            safe_print(f"    {key}: {val}")
                if check.get("note"):
                    safe_print(f"    Note: {check['note']}")
            if rec.signals:
                safe_print(f"  Signals: {', '.join(rec.signals[:3])}")
            safe_print("")

    if medium_conf:
        safe_print("MEDIUM CONFIDENCE RECOMMENDATIONS:")
        safe_print("")
        for rec in medium_conf:
            safe_print(f"? {rec.column} ({rec.data_type}) - confidence: {rec.confidence:.2f}")
            checks = [c["type"] for c in rec.suggested_checks]
            safe_print(f"  Suggested: {', '.join(checks)}")
        safe_print("")

    if low_conf:
        safe_print("LOW CONFIDENCE SUGGESTIONS:")
        safe_print("")
        for rec in low_conf:
            safe_print(f"○ {rec.column} ({rec.data_type}) - confidence: {rec.confidence:.2f}")
            safe_print("  Consider manual inspection")
        safe_print("")


def _apply_recommendations(
    config_path: str, report, config: BaselinrConfig, include_columns: bool = False
):
    """Apply recommendations by updating the configuration file."""
    from pathlib import Path

    import yaml  # type: ignore

    # Load raw config file
    config_file = Path(config_path)
    with open(config_file, "r") as f:
        raw_config = yaml.safe_load(f)

    # Ensure profiling.tables exists
    if "profiling" not in raw_config:
        raw_config["profiling"] = {}
    if "tables" not in raw_config["profiling"]:
        raw_config["profiling"]["tables"] = []

    # Add recommended tables (with optional column recommendations)
    for rec in report.recommended_tables:
        table_entry = {
            "schema": rec.schema,
            "table": rec.table,
        }
        if rec.database:
            table_entry["database"] = rec.database

        # Add comment about recommendation
        table_entry["_comment"] = f"Auto-recommended (confidence: {rec.confidence:.2f})"

        # Add column-level checks if enabled and recommendations exist
        if (
            include_columns
            and hasattr(rec, "column_recommendations")
            and rec.column_recommendations
        ):
            columns_config = []
            for col_rec in rec.column_recommendations:
                col_entry = {
                    "name": col_rec.column,
                    "_comment": f"confidence: {col_rec.confidence:.2f}",
                }
                # Add validation rules as checks if available
                if col_rec.suggested_checks:
                    # Just add a note about suggested checks
                    checks_summary = [c["type"] for c in col_rec.suggested_checks]
                    col_entry["_suggested_checks"] = checks_summary
                columns_config.append(col_entry)

            if columns_config:
                table_entry["columns"] = columns_config

        raw_config["profiling"]["tables"].append(table_entry)

    # Backup original config
    backup_path = config_file.with_suffix(config_file.suffix + ".backup")
    import shutil

    shutil.copy(config_file, backup_path)
    logger.info(f"Created backup: {backup_path}")

    # Write updated config
    with open(config_file, "w") as f:
        yaml.dump(raw_config, f, default_flow_style=False, sort_keys=False)


def rca_command(args):
    """Execute RCA command."""
    from .cli_output import safe_print
    from .connectors.factory import create_connector
    from .rca.collectors import DagsterRunCollector, DbtRunCollector
    from .rca.service import RCAService

    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)

        if not config.rca.enabled:
            safe_print("❌ RCA is disabled in configuration")
            return 1

        # Create storage connector
        storage_connector = create_connector(config.storage.connection)
        engine = storage_connector.engine

        if args.rca_command == "analyze":
            # Parse timestamp
            from datetime import datetime

            from .rca.models import parse_fully_qualified_table

            if args.timestamp:
                try:
                    anomaly_timestamp = datetime.fromisoformat(
                        args.timestamp.replace("Z", "+00:00")
                    )
                except ValueError:
                    safe_print(f"❌ Invalid timestamp format: {args.timestamp}")
                    return 1
            else:
                anomaly_timestamp = datetime.utcnow()

            # Parse fully qualified table name (database.schema.table, schema.table, or table)
            database_name, schema_name, table_name = parse_fully_qualified_table(args.table)
            # Override with explicit args if provided (for backward compatibility)
            if args.schema:
                schema_name = args.schema

            # Initialize RCA service
            service = RCAService(
                engine=engine,
                auto_analyze=False,
                lookback_window_hours=config.rca.lookback_window_hours,
                max_depth=config.rca.max_depth,
                max_causes_to_return=config.rca.max_causes_to_return,
                min_confidence_threshold=config.rca.min_confidence_threshold,
                enable_pattern_learning=config.rca.enable_pattern_learning,
            )

            # Perform analysis
            result = service.analyze_anomaly(
                anomaly_id=args.anomaly_id,
                table_name=table_name,
                anomaly_timestamp=anomaly_timestamp,
                database_name=database_name,
                schema_name=schema_name,
                column_name=args.column,
                metric_name=args.metric,
            )

            # Output results
            if args.format == "json":
                import json

                output = {
                    "anomaly_id": result.anomaly_id,
                    "table_name": result.table_name,
                    "schema_name": result.schema_name,
                    "column_name": result.column_name,
                    "metric_name": result.metric_name,
                    "analyzed_at": result.analyzed_at.isoformat() if result.analyzed_at else None,
                    "rca_status": result.rca_status,
                    "probable_causes": result.probable_causes,
                    "impact_analysis": result.impact_analysis,
                }
                print(json.dumps(output, indent=2, default=str))
            else:
                safe_print(f"\n📊 RCA Results for {result.anomaly_id}")
                table_display = result.table_name
                if result.database_name and result.schema_name:
                    table_display = (
                        f"{result.database_name}.{result.schema_name}.{result.table_name}"
                    )
                elif result.schema_name:
                    table_display = f"{result.schema_name}.{result.table_name}"
                safe_print(f"Table: {table_display}")
                if result.column_name:
                    safe_print(f"Column: {result.column_name}")
                if result.metric_name:
                    safe_print(f"Metric: {result.metric_name}")
                safe_print(f"Status: {result.rca_status}")
                safe_print(f"\nFound {len(result.probable_causes)} probable causes:\n")

                for i, cause in enumerate(result.probable_causes, 1):
                    safe_print(f"{i}. {cause.get('description', 'Unknown cause')}")
                    safe_print(f"   Confidence: {cause.get('confidence_score', 0):.2%}")
                    safe_print(f"   Type: {cause.get('cause_type', 'unknown')}")
                    if cause.get("suggested_action"):
                        safe_print(f"   Action: {cause.get('suggested_action')}")
                    safe_print("")

            return 0

        elif args.rca_command == "list":
            service = RCAService(engine=engine, auto_analyze=False)
            results = service.get_recent_rca_results(limit=args.limit)

            if args.format == "json":
                import json

                print(json.dumps(results, indent=2, default=str))
            else:
                safe_print(f"\n📋 Recent RCA Results (showing {len(results)})\n")
                for result in results:
                    safe_print(f"Anomaly: {result['anomaly_id']}")
                    safe_print(f"  Table: {result['table_name']}")
                    safe_print(f"  Status: {result['rca_status']}")
                    safe_print(f"  Causes: {result['num_causes']}")
                    safe_print("")

            return 0

        elif args.rca_command == "get":
            service = RCAService(engine=engine, auto_analyze=False)
            result = service.get_rca_result(args.anomaly_id)

            if not result:
                safe_print(f"❌ No RCA result found for anomaly: {args.anomaly_id}")
                return 1

            if args.format == "json":
                import json

                output = {
                    "anomaly_id": result.anomaly_id,
                    "database_name": result.database_name,
                    "table_name": result.table_name,
                    "schema_name": result.schema_name,
                    "column_name": result.column_name,
                    "metric_name": result.metric_name,
                    "analyzed_at": result.analyzed_at.isoformat() if result.analyzed_at else None,
                    "rca_status": result.rca_status,
                    "probable_causes": result.probable_causes,
                    "impact_analysis": result.impact_analysis,
                }
                print(json.dumps(output, indent=2, default=str))
            else:
                safe_print(f"\n📊 RCA Result for {result.anomaly_id}")
                table_display = result.table_name
                if result.database_name and result.schema_name:
                    table_display = (
                        f"{result.database_name}.{result.schema_name}.{result.table_name}"
                    )
                elif result.schema_name:
                    table_display = f"{result.schema_name}.{result.table_name}"
                safe_print(f"Table: {table_display}")
                safe_print(f"Status: {result.rca_status}")
                safe_print(f"Causes: {len(result.probable_causes)}\n")

                for i, cause in enumerate(result.probable_causes, 1):
                    safe_print(f"{i}. {cause.get('description', 'Unknown cause')}")
                    safe_print(f"   Confidence: {cause.get('confidence_score', 0):.2%}")
                    safe_print("")

            return 0

        elif args.rca_command == "collect":
            collectors_to_run = []
            if args.type in ["dbt", "all"] and (
                config.rca.collectors.dbt or config.rca.collectors.dbt is None
            ):
                collector = DbtRunCollector(
                    engine=engine,
                    manifest_path=config.rca.collectors.manifest_path,
                    project_dir=config.rca.collectors.project_dir,
                )
                collectors_to_run.append(("dbt", collector))

            if args.type in ["dagster", "all"] and config.rca.collectors.dagster:
                collector = DagsterRunCollector(
                    engine=engine,
                    instance_path=config.rca.collectors.dagster_instance_path,
                    graphql_url=config.rca.collectors.dagster_graphql_url,
                )
                collectors_to_run.append(("dagster", collector))

            if not collectors_to_run:
                safe_print("❌ No collectors enabled or configured")
                return 1

            total_collected = 0
            for name, collector in collectors_to_run:
                safe_print(f"Collecting {name} runs...")
                count = collector.collect_and_store()
                total_collected += count
                safe_print(f"✅ Collected {count} {name} runs")

            safe_print(f"\n✨ Total: {total_collected} runs collected")
            return 0

        else:
            safe_print(f"❌ Unknown RCA command: {args.rca_command}")
            return 1

    except Exception as e:
        logger.error(f"RCA command failed: {e}", exc_info=True)
        safe_print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


def contracts_command(args):
    """Execute contracts command."""
    from .cli_output import safe_print
    from .client import BaselinrClient

    try:
        # Initialize client (loads config and contracts)
        client = BaselinrClient(config_path=args.config)

        if args.contracts_command == "list":
            contracts = client.contracts

            if args.format == "json":
                output = []
                for contract in contracts:
                    output.append(
                        {
                            "id": contract.id,
                            "status": contract.status,
                            "title": contract.info.title if contract.info else None,
                            "owner": contract.info.owner if contract.info else None,
                            "domain": contract.info.domain if contract.info else None,
                            "datasets": contract.get_dataset_names(),
                            "quality_rules": len(contract.get_all_quality_rules()),
                            "service_levels": len(contract.servicelevels or []),
                        }
                    )
                print(json.dumps(output, indent=2))
            else:
                safe_print(f"\n📋 ODCS Contracts ({len(contracts)} loaded)\n")

                if not contracts:
                    safe_print("No contracts found. Check your contracts directory in config.")
                    return 0

                for contract in contracts:
                    contract_id = contract.id or "unnamed"
                    title = contract.info.title if contract.info else "Untitled"
                    status = contract.status or "unknown"

                    safe_print(f"📄 {contract_id}")
                    safe_print(f"   Title: {title}")
                    safe_print(f"   Status: {status}")

                    if contract.info:
                        if contract.info.owner:
                            safe_print(f"   Owner: {contract.info.owner}")
                        if contract.info.domain:
                            safe_print(f"   Domain: {contract.info.domain}")

                    datasets = contract.get_dataset_names()
                    if datasets:
                        safe_print(f"   Datasets: {', '.join(datasets)}")

                    rules_count = len(contract.get_all_quality_rules())
                    sla_count = len(contract.servicelevels or [])
                    safe_print(f"   Quality Rules: {rules_count}")
                    safe_print(f"   Service Levels: {sla_count}")

                    if args.verbose and contract.dataset:
                        for ds in contract.dataset:
                            cols = len(ds.columns) if ds.columns else 0
                            safe_print(f"     └─ {ds.name}: {cols} columns")

                    safe_print("")

                safe_print(f"Total: {len(contracts)} contract(s)")

            return 0

        elif args.contracts_command == "validate":
            result = client.validate_contracts(strict=args.strict)

            if args.format == "json":
                print(json.dumps(result, indent=2))
            else:
                safe_print("\n🔍 Contract Validation Results\n")
                safe_print(f"Contracts checked: {result['contracts_checked']}")
                safe_print(f"Valid: {'✅ Yes' if result['valid'] else '❌ No'}")

                if result["errors"]:
                    safe_print(f"\n❌ Errors ({len(result['errors'])}):")
                    for error in result["errors"]:
                        safe_print(f"   [{error['contract']}] {error['message']}")

                if result["warnings"]:
                    safe_print(f"\n⚠️  Warnings ({len(result['warnings'])}):")
                    for warning in result["warnings"]:
                        safe_print(f"   [{warning['contract']}] {warning['message']}")

                if result["valid"]:
                    safe_print("\n✅ All contracts are valid!")

            return 0 if result["valid"] else 1

        elif args.contracts_command == "show":
            contract = client.get_contract(args.contract)

            if not contract:
                safe_print(f"❌ Contract not found: {args.contract}")
                return 1

            if args.format == "json":
                # Convert to dict and output as JSON
                output = contract.model_dump(exclude_none=True)
                print(json.dumps(output, indent=2, default=str))
            elif args.format == "yaml":
                import yaml

                output = contract.model_dump(exclude_none=True)
                print(yaml.dump(output, default_flow_style=False, sort_keys=False))
            else:
                # Table format
                safe_print(f"\n📄 Contract: {contract.id or 'unnamed'}")
                safe_print(f"   API Version: {contract.apiVersion}")
                safe_print(f"   Status: {contract.status or 'unknown'}")

                if contract.info:
                    safe_print("\n📝 Info:")
                    if contract.info.title:
                        safe_print(f"   Title: {contract.info.title}")
                    if contract.info.description:
                        safe_print(f"   Description: {contract.info.description}")
                    if contract.info.owner:
                        safe_print(f"   Owner: {contract.info.owner}")
                    if contract.info.domain:
                        safe_print(f"   Domain: {contract.info.domain}")

                if contract.dataset:
                    safe_print(f"\n📊 Datasets ({len(contract.dataset)}):")
                    for ds in contract.dataset:
                        safe_print(f"   • {ds.name} ({ds.type or 'table'})")
                        if ds.physicalName:
                            safe_print(f"     Physical: {ds.physicalName}")
                        if ds.description:
                            safe_print(f"     {ds.description[:60]}...")
                        if ds.columns:
                            safe_print(f"     Columns: {len(ds.columns)}")
                            for col in ds.columns[:5]:
                                pk = " [PK]" if col.isPrimaryKey else ""
                                nullable = " (nullable)" if col.isNullable else " (required)"
                                col_type = col.logicalType or "unknown"
                                safe_print(f"       - {col.name}: {col_type}{pk}{nullable}")
                            if len(ds.columns) > 5:
                                safe_print(f"       ... and {len(ds.columns) - 5} more")

                rules = contract.get_all_quality_rules()
                if rules:
                    safe_print(f"\n✅ Quality Rules ({len(rules)}):")
                    for rule in rules[:5]:
                        rule_type = rule.rule or rule.type or "check"
                        col = rule.column or (
                            rule.specification.column if rule.specification else None
                        )
                        col_str = f" on {col}" if col else ""
                        safe_print(f"   • {rule_type}{col_str} ({rule.severity or 'error'})")
                    if len(rules) > 5:
                        safe_print(f"   ... and {len(rules) - 5} more")

                if contract.servicelevels:
                    safe_print(f"\n⏱️  Service Levels ({len(contract.servicelevels)}):")
                    for sla in contract.servicelevels:
                        unit = f" {sla.unit}" if sla.unit else ""
                        safe_print(f"   • {sla.property}: {sla.value}{unit}")

                if contract.stakeholders:
                    safe_print(f"\n👥 Stakeholders ({len(contract.stakeholders)}):")
                    for sh in contract.stakeholders[:3]:
                        name = sh.name or sh.username or sh.email or "unknown"
                        role = f" ({sh.role})" if sh.role else ""
                        safe_print(f"   • {name}{role}")
                    if len(contract.stakeholders) > 3:
                        safe_print(f"   ... and {len(contract.stakeholders) - 3} more")

            return 0

        elif args.contracts_command == "rules":
            rules = client.get_validation_rules_from_contracts()

            # Filter by contract if specified
            if args.contract:
                rules = [r for r in rules if r.contract_id == args.contract]

            if args.format == "json":
                output = []
                for rule in rules:
                    output.append(
                        {
                            "type": rule.type,
                            "table": rule.table,
                            "column": rule.column,
                            "severity": rule.severity,
                            "dimension": rule.dimension,
                            "description": rule.description,
                            "contract_id": rule.contract_id,
                        }
                    )
                print(json.dumps(output, indent=2))
            else:
                safe_print(f"\n✅ Validation Rules from Contracts ({len(rules)} total)\n")

                if not rules:
                    safe_print("No validation rules found in contracts.")
                    return 0

                # Group by table
                rules_by_table = {}
                for rule in rules:
                    table = rule.table or "unknown"
                    if table not in rules_by_table:
                        rules_by_table[table] = []
                    rules_by_table[table].append(rule)

                for table, table_rules in rules_by_table.items():
                    safe_print(f"📋 {table} ({len(table_rules)} rules)")
                    for rule in table_rules:
                        col_str = f".{rule.column}" if rule.column else ""
                        desc = f" - {rule.description[:40]}..." if rule.description else ""
                        safe_print(f"   • [{rule.severity}] {rule.type}{col_str}{desc}")
                    safe_print("")

            return 0

        else:
            safe_print(f"❌ Unknown contracts command: {args.contracts_command}")
            return 1

    except Exception as e:
        logger.error(f"Contracts command failed: {e}", exc_info=True)
        safe_print(f"\n❌ Error: {e}")
        if hasattr(args, "debug") and args.debug:
            import traceback

            traceback.print_exc()
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Baselinr - Data profiling and drift detection")

    # Global --debug flag (affects all commands)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output and verbose logging",
    )

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

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Execute data validation rules")
    validate_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file (YAML or JSON)"
    )
    validate_parser.add_argument("--table", help="Filter validation to specific table")
    validate_parser.add_argument("--output", "-o", help="Output file for results (JSON)")

    # Score command
    score_parser = subparsers.add_parser(
        "score",
        help="Calculate and display data quality scores",
        description=(
            "Calculate comprehensive data quality scores that combine multiple "
            "dimensions (completeness, validity, consistency, freshness, "
            "uniqueness, accuracy) into a single actionable score (0-100). "
            "Scores help identify and prioritize data quality issues."
        ),
        epilog=(
            "Examples:\n"
            "  # Calculate score for a table\n"
            "  baselinr score --config config.yaml --table customers\n\n"
            "  # Export score to CSV\n"
            "  baselinr score --config config.yaml --table customers "
            "--export csv --output scores.csv\n\n"
            "  # Export score history\n"
            "  baselinr score --config config.yaml --table customers "
            "--history --export json --output history.json\n\n"
            "  # Get JSON output\n"
            "  baselinr score --config config.yaml --table customers --format json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    score_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file (YAML or JSON)"
    )
    score_parser.add_argument(
        "--table", required=True, help="Table name to calculate score for", metavar="TABLE"
    )
    score_parser.add_argument(
        "--schema", help="Schema name (optional, filters by schema if provided)"
    )
    score_parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help=(
            "Output format: 'table' for formatted display (default), "
            "'json' for machine-readable output"
        ),
    )
    score_parser.add_argument(
        "--export",
        choices=["csv", "json"],
        help=(
            "Export scores to file. Use 'csv' for spreadsheet-compatible "
            "format or 'json' for structured data. Requires --output."
        ),
    )
    score_parser.add_argument(
        "--output",
        help="Output file path for export (required when using --export)",
        metavar="FILE",
    )
    score_parser.add_argument(
        "--history",
        action="store_true",
        help=(
            "Export score history instead of single score. "
            "Use with --export to get historical data."
        ),
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

    # Lineage command
    lineage_parser = subparsers.add_parser("lineage", help="Query data lineage")
    lineage_subparsers = lineage_parser.add_subparsers(
        dest="lineage_command", help="Lineage operation"
    )

    # lineage upstream
    upstream_parser = lineage_subparsers.add_parser("upstream", help="Get upstream dependencies")
    upstream_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    upstream_parser.add_argument("--table", required=True, help="Table name")
    upstream_parser.add_argument("--schema", help="Schema name")
    upstream_parser.add_argument("--column", help="Column name (for column-level lineage)")
    upstream_parser.add_argument(
        "--max-depth", type=int, help="Maximum depth to traverse (default: unlimited)"
    )
    upstream_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )
    upstream_parser.add_argument("--output", "-o", help="Output file")

    # lineage downstream
    downstream_parser = lineage_subparsers.add_parser(
        "downstream", help="Get downstream dependencies"
    )
    downstream_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    downstream_parser.add_argument("--table", required=True, help="Table name")
    downstream_parser.add_argument("--schema", help="Schema name")
    downstream_parser.add_argument("--column", help="Column name (for column-level lineage)")
    downstream_parser.add_argument(
        "--max-depth", type=int, help="Maximum depth to traverse (default: unlimited)"
    )
    downstream_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )
    downstream_parser.add_argument("--output", "-o", help="Output file")

    # lineage path
    path_parser = lineage_subparsers.add_parser("path", help="Find path between two tables")
    path_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    path_parser.add_argument(
        "--from", dest="from_table", required=True, help="Source table (schema.table)"
    )
    path_parser.add_argument(
        "--to", dest="to_table", required=True, help="Target table (schema.table)"
    )
    path_parser.add_argument("--from-column", help="Source column (for column-level lineage)")
    path_parser.add_argument("--to-column", help="Target column (for column-level lineage)")
    path_parser.add_argument(
        "--max-depth", type=int, help="Maximum depth to search (default: unlimited)"
    )
    path_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )
    path_parser.add_argument("--output", "-o", help="Output file")

    # lineage providers
    providers_parser = lineage_subparsers.add_parser("providers", help="List available providers")
    providers_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    providers_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # lineage sync
    sync_parser = lineage_subparsers.add_parser(
        "sync", help="Sync lineage from query history (bulk operation)"
    )
    sync_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    sync_parser.add_argument(
        "--provider",
        help="Specific provider to sync (e.g., postgres_query_history, snowflake_query_history)",
    )
    sync_parser.add_argument("--all", action="store_true", help="Sync all query history providers")
    sync_parser.add_argument("--lookback-days", type=int, help="Override lookback days from config")
    sync_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be extracted without writing"
    )
    sync_parser.add_argument(
        "--force", action="store_true", help="Force full resync (ignore last sync timestamp)"
    )

    # lineage cleanup
    cleanup_parser = lineage_subparsers.add_parser(
        "cleanup", help="Clean up stale lineage edges from query history"
    )
    cleanup_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    cleanup_parser.add_argument(
        "--provider",
        help=(
            "Specific provider to clean up "
            "(e.g., postgres_query_history, snowflake_query_history)"
        ),
    )
    cleanup_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be deleted without deleting"
    )
    cleanup_parser.add_argument(
        "--expiration-days", type=int, help="Override expiration days from config"
    )

    # lineage visualize
    visualize_parser = lineage_subparsers.add_parser(
        "visualize", help="Visualize lineage as diagram or export to various formats"
    )
    visualize_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    visualize_parser.add_argument("--table", required=True, help="Table name")
    visualize_parser.add_argument("--schema", help="Schema name")
    visualize_parser.add_argument("--column", help="Column name (for column-level lineage)")
    visualize_parser.add_argument(
        "--direction",
        choices=["upstream", "downstream", "both"],
        default="both",
        help="Lineage direction to show (default: both)",
    )
    visualize_parser.add_argument(
        "--depth", type=int, default=3, help="Maximum depth to traverse (default: 3)"
    )
    visualize_parser.add_argument(
        "--format",
        choices=["ascii", "mermaid", "dot", "json", "svg", "png", "pdf"],
        default="ascii",
        help="Output format (default: ascii)",
    )
    visualize_parser.add_argument(
        "--json-format",
        choices=["cytoscape", "d3", "generic"],
        default="generic",
        help="JSON export format (default: generic)",
    )
    visualize_parser.add_argument("--output", "-o", help="Output file path")
    visualize_parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output (ASCII format)"
    )
    visualize_parser.add_argument(
        "--highlight-drift",
        action="store_true",
        help="Highlight tables with drift",
    )
    visualize_parser.add_argument(
        "--layout",
        action="store_true",
        help="Include layout positions in JSON export",
    )

    # lineage show (NEW - Phase 3)
    show_parser = lineage_subparsers.add_parser(
        "show", help="Show lineage for a table with impact scoring"
    )
    show_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    show_parser.add_argument("--table", required=True, help="Table name")
    show_parser.add_argument("--schema", help="Schema name")
    show_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )
    show_parser.add_argument("--output", "-o", help="Output file path")

    # lineage impact (NEW - Phase 3)
    impact_parser = lineage_subparsers.add_parser("impact", help="Show blast radius for a table")
    impact_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    impact_parser.add_argument("--table", required=True, help="Table name")
    impact_parser.add_argument("--schema", help="Schema name")
    impact_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )
    impact_parser.add_argument("--output", "-o", help="Output file path")

    # lineage validate (NEW - Phase 3)
    validate_parser = lineage_subparsers.add_parser(
        "validate", help="Validate lineage availability and graph structure"
    )
    validate_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    validate_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # lineage refresh-cache (NEW - Phase 3)
    refresh_parser = lineage_subparsers.add_parser("refresh-cache", help="Refresh lineage cache")
    refresh_parser.add_argument("--config", "-c", required=True, help="Configuration file")

    # Recommend command
    recommend_parser = subparsers.add_parser(
        "recommend",
        help="Generate smart table and column check recommendations based on usage patterns",
    )
    recommend_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file (YAML or JSON)"
    )
    recommend_parser.add_argument(
        "--output",
        "-o",
        help="Output file for recommendations (default: recommendations.yaml)",
    )
    recommend_parser.add_argument(
        "--schema",
        "-s",
        help="Limit recommendations to specific schema",
    )
    recommend_parser.add_argument(
        "--table",
        "-t",
        help="Recommend checks for a specific table (use with --columns)",
    )
    recommend_parser.add_argument(
        "--columns",
        action="store_true",
        help="Include column-level check recommendations",
    )
    recommend_parser.add_argument(
        "--explain",
        action="store_true",
        help="Show detailed explanations for recommendations",
    )
    recommend_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply recommendations by merging into config file (prompt for confirmation)",
    )
    recommend_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what checks would be added without applying",
    )
    recommend_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh recommendations based on latest metadata",
    )
    recommend_parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    recommend_parser.add_argument(
        "--with-lineage",
        action="store_true",
        help="Include lineage-aware scoring in recommendations",
    )
    recommend_parser.add_argument(
        "--explain-lineage",
        action="store_true",
        help="Show detailed lineage explanation for a specific table",
    )
    recommend_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
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

    # RCA command
    rca_parser = subparsers.add_parser("rca", help="Root Cause Analysis operations")
    rca_subparsers = rca_parser.add_subparsers(dest="rca_command", help="RCA operation")

    # rca analyze
    analyze_parser = rca_subparsers.add_parser("analyze", help="Analyze an anomaly")
    analyze_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    analyze_parser.add_argument("--anomaly-id", required=True, help="Anomaly ID to analyze")
    analyze_parser.add_argument(
        "--table",
        required=True,
        help="Fully qualified table name (database.schema.table, schema.table, or table)",
    )
    analyze_parser.add_argument(
        "--schema", help="Schema name (optional, overrides schema from --table if provided)"
    )
    analyze_parser.add_argument("--column", help="Column name")
    analyze_parser.add_argument("--metric", help="Metric name")
    analyze_parser.add_argument(
        "--timestamp",
        help="Anomaly timestamp (ISO format, default: now)",
    )
    analyze_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # rca list
    list_parser = rca_subparsers.add_parser("list", help="List recent RCA results")
    list_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    list_parser.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    list_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # rca get
    get_parser = rca_subparsers.add_parser("get", help="Get specific RCA result")
    get_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    get_parser.add_argument("--anomaly-id", required=True, help="Anomaly ID")
    get_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    # rca collect
    collect_parser = rca_subparsers.add_parser("collect", help="Collect pipeline runs")
    collect_parser.add_argument("--config", "-c", required=True, help="Configuration file")
    collect_parser.add_argument(
        "--type",
        choices=["dbt", "dagster", "all"],
        default="all",
        help="Collector type (default: all)",
    )

    # Chat command
    chat_parser = subparsers.add_parser(
        "chat",
        help="Start interactive chat session for data quality investigation",
    )
    chat_parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to configuration file (YAML or JSON)",
    )
    chat_parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum tool-calling iterations (default: 5)",
    )
    chat_parser.add_argument(
        "--max-history",
        type=int,
        default=20,
        help="Maximum messages to keep in context (default: 20)",
    )
    chat_parser.add_argument(
        "--tool-timeout",
        type=int,
        default=30,
        help="Tool execution timeout in seconds (default: 30)",
    )
    chat_parser.add_argument(
        "--show-tools",
        action="store_true",
        help="Show tool calls in output",
    )
    chat_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    # Contracts command
    contracts_parser = subparsers.add_parser(
        "contracts",
        help="Manage ODCS data contracts",
        description=(
            "Work with ODCS (Open Data Contract Standard) data contracts. "
            "Contracts define dataset schemas, quality rules, SLAs, and ownership."
        ),
    )
    contracts_subparsers = contracts_parser.add_subparsers(
        dest="contracts_command", help="Contracts operation"
    )

    # contracts list
    contracts_list_parser = contracts_subparsers.add_parser("list", help="List loaded contracts")
    contracts_list_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file"
    )
    contracts_list_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    contracts_list_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose details"
    )

    # contracts validate
    contracts_validate_parser = contracts_subparsers.add_parser(
        "validate", help="Validate ODCS contracts"
    )
    contracts_validate_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file"
    )
    contracts_validate_parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )
    contracts_validate_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    # contracts show
    contracts_show_parser = contracts_subparsers.add_parser(
        "show", help="Show details of a specific contract"
    )
    contracts_show_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file"
    )
    contracts_show_parser.add_argument(
        "--contract", required=True, help="Contract ID or dataset name"
    )
    contracts_show_parser.add_argument(
        "--format",
        choices=["table", "json", "yaml"],
        default="table",
        help="Output format (default: table)",
    )

    # contracts rules
    contracts_rules_parser = contracts_subparsers.add_parser(
        "rules", help="List validation rules from contracts"
    )
    contracts_rules_parser.add_argument(
        "--config", "-c", required=True, help="Path to configuration file"
    )
    contracts_rules_parser.add_argument("--contract", help="Filter by contract ID or dataset name")
    contracts_rules_parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Set debug logging level if --debug flag is present
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        # Also set level for all baselinr loggers
        logging.getLogger("baselinr").setLevel(logging.DEBUG)

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
    elif args.command == "validate":
        return validate_command(args)
    elif args.command == "score":
        return score_command(args)
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
    elif args.command == "lineage":
        if not args.lineage_command:
            lineage_parser.print_help()
            return 1
        # Handle visualize subcommand separately
        if args.lineage_command == "visualize":
            return lineage_visualize_command(args)
        return lineage_command(args)
    elif args.command == "ui":
        return ui_command(args)
    elif args.command == "recommend":
        return recommend_command(args)
    elif args.command == "rca":
        if not args.rca_command:
            rca_parser.print_help()
            return 1
        return rca_command(args)
    elif args.command == "chat":
        return chat_command(args)
    elif args.command == "contracts":
        if not args.contracts_command:
            contracts_parser.print_help()
            return 1
        return contracts_command(args)
    else:
        parser.print_help()
        return 1


def _select_tables_from_plan(plan: IncrementalPlan, config: BaselinrConfig):
    """Convert plan decisions into table patterns for execution.

    Note: Partition and sampling overrides for incremental runs are now handled
    via ODCS contracts. The incremental planner decisions are used to determine
    which tables to run, but partition/sampling configs come from contracts.
    """
    selected = []
    for decision in plan.decisions:
        if decision.action not in ("full", "partial", "sample"):
            continue
        pattern = decision.table
        table_pattern = pattern.model_copy(deep=True)

        # Note: Partition and sampling configs are now in ODCS contracts.
        # For partial runs, the partition config should be defined in the contract
        # customProperties with strategy "specific_values" and the values set there.
        # For sampling, the contract should have sampling config in customProperties.
        # The incremental planner decisions are used to determine which tables
        # to run, but the actual partition/sampling configs come from contracts.

        if decision.action == "partial" and decision.changed_partitions:
            # Check if partition config exists in datasets
            from .config.merger import ConfigMerger

            merger = ConfigMerger(config)
            profiling_config = merger.merge_profiling_config(
                table_pattern=table_pattern,
                database_name=table_pattern.database,
                schema=table_pattern.schema_,
                table=table_pattern.table,
            )
            if not profiling_config.get("partition") or not profiling_config["partition"].key:
                logger.warning(
                    "Partial run requested for %s but no partition key configured in datasets; "
                    "falling back to full scan",
                    pattern.table,
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
        # Try to find matching decision - need to check all possible keys
        # since database might not be in result.
        # First try without database, then with database from decision if available
        key = _plan_table_key_raw(result.schema_name, result.dataset_name)
        decision = decision_map.get(key)

        # If not found, try with database from decision table pattern
        if not decision:
            for dec in plan.decisions:
                if dec.action in ("full", "partial", "sample") and dec.table:
                    if (
                        dec.table.table == result.dataset_name
                        and dec.table.schema_ == result.schema_name
                    ):
                        decision = dec
                        break

        # Get database from decision table pattern if available, otherwise None
        database_name = decision.table.database if decision and decision.table else None

        state = TableState(
            table_name=result.dataset_name,
            schema_name=result.schema_name,
            database_name=database_name,
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
    assert pattern.table is not None, "Table name must be set"
    return _plan_table_key_raw(pattern.schema_, pattern.table, pattern.database)


def _plan_table_key_raw(schema: Optional[str], table: str, database: Optional[str] = None) -> str:
    """Generate table key including database, schema, and table name."""
    parts = []
    if database:
        parts.append(database)
    if schema:
        parts.append(schema)
    parts.append(table)
    return ".".join(parts)


if __name__ == "__main__":
    sys.exit(main())

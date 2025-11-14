"""
Command-line interface for ProfileMesh.

Provides CLI commands for profiling tables and detecting drift.
"""

import sys
import argparse
import logging
import json
import importlib
from pathlib import Path
from typing import Optional

from .config.loader import ConfigLoader
from .config.schema import ProfileMeshConfig, HookConfig
from .profiling.core import ProfileEngine
from .storage.writer import ResultWriter
from .drift.detector import DriftDetector
from .planner import PlanBuilder, print_plan
from .events import EventBus, LoggingAlertHook, SnowflakeEventHook, SQLEventHook
from .logging import RunContext, log_event, log_and_emit

# Setup fallback logging (will be replaced by structured logging per command)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_event_bus(config: ProfileMeshConfig) -> Optional[EventBus]:
    """
    Create and configure an event bus from configuration.
    
    Args:
        config: ProfileMesh configuration
        
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
        connector = SnowflakeConnector(hook_config.connection)
        table_name = hook_config.table_name or "profilemesh_events"
        return SnowflakeEventHook(engine=connector.engine, table_name=table_name)
    
    elif hook_config.type == "sql":
        if not hook_config.connection:
            raise ValueError("SQL hook requires connection configuration")
        
        # Create engine based on connection type
        from .connectors import (
            PostgresConnector, SQLiteConnector, MySQLConnector,
            BigQueryConnector, RedshiftConnector
        )
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
        
        table_name = hook_config.table_name or "profilemesh_events"
        return SQLEventHook(engine=connector.engine, table_name=table_name)
    
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
    # Create run context with structured logging
    ctx = RunContext.create(component="cli")
    
    log_event(ctx.logger, "command_started", f"Loading configuration from: {args.config}",
              metadata={"config_path": args.config, "command": "profile"})
    
    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)
        log_event(ctx.logger, "config_loaded", f"Configuration loaded for environment: {config.environment}",
                  metadata={"environment": config.environment})
        
        # Create event bus and register hooks
        event_bus = create_event_bus(config)
        if event_bus:
            log_event(ctx.logger, "event_bus_initialized", 
                     f"Event bus initialized with {event_bus.hook_count} hooks",
                     metadata={"hook_count": event_bus.hook_count})
        
        # Create profiling engine with run context
        engine = ProfileEngine(config, event_bus=event_bus, run_context=ctx)
        
        # Run profiling
        log_event(ctx.logger, "profiling_batch_started", "Starting profiling...")
        results = engine.profile()
        
        if not results:
            log_event(ctx.logger, "no_results", "No profiling results generated", level="warning")
            return 1
        
        log_event(ctx.logger, "profiling_batch_completed", f"Profiling completed: {len(results)} tables profiled",
                  metadata={"table_count": len(results)})
        
        # Write results to storage
        if not args.dry_run:
            log_event(ctx.logger, "storage_write_started", "Writing results to storage...")
            writer = ResultWriter(config.storage)
            writer.write_results(results, environment=config.environment)
            log_event(ctx.logger, "storage_write_completed", "Results written successfully",
                      metadata={"result_count": len(results)})
            writer.close()
        else:
            log_event(ctx.logger, "dry_run", "Dry run - results not written to storage")
        
        # Output results
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump([r.to_dict() for r in results], f, indent=2)
            log_event(ctx.logger, "results_exported", f"Results saved to: {args.output}",
                      metadata={"output_path": str(args.output)})
        
        # Print summary
        for result in results:
            print(f"\n{'='*60}")
            print(f"Dataset: {result.dataset_name}")
            print(f"Run ID: {result.run_id}")
            print(f"Profiled at: {result.profiled_at}")
            print(f"Columns profiled: {len(result.columns)}")
            print(f"Row count: {result.metadata.get('row_count', 'N/A')}")
        
        return 0
    
    except Exception as e:
        log_event(ctx.logger, "error", f"Profiling failed: {e}",
                  level="error", metadata={"error": str(e), "error_type": type(e).__name__})
        return 1


def drift_command(args):
    """Execute drift detection command."""
    logger.info(f"Loading configuration from: {args.config}")
    
    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)
        
        # Create event bus and register hooks
        event_bus = create_event_bus(config)
        if event_bus:
            logger.info(f"Event bus initialized with {event_bus.hook_count} hooks")
        
        # Create drift detector with drift detection config and event bus
        detector = DriftDetector(config.storage, config.drift_detection, event_bus=event_bus)
        
        # Detect drift
        logger.info(f"Detecting drift for dataset: {args.dataset}")
        report = detector.detect_drift(
            dataset_name=args.dataset,
            baseline_run_id=args.baseline,
            current_run_id=args.current,
            schema_name=args.schema
        )
        
        # Print report
        print(f"\n{'='*60}")
        print("DRIFT DETECTION REPORT")
        print(f"{'='*60}")
        print(f"Dataset: {report.dataset_name}")
        print(f"Baseline: {report.baseline_run_id} ({report.baseline_timestamp})")
        print(f"Current: {report.current_run_id} ({report.current_timestamp})")
        print(f"\nSummary:")
        print(f"  Total drifts detected: {report.summary['total_drifts']}")
        print(f"  Schema changes: {report.summary['schema_changes']}")
        print(f"  High severity: {report.summary['drift_by_severity']['high']}")
        print(f"  Medium severity: {report.summary['drift_by_severity']['medium']}")
        print(f"  Low severity: {report.summary['drift_by_severity']['low']}")
        
        if report.schema_changes:
            print(f"\nSchema Changes:")
            for change in report.schema_changes:
                print(f"  - {change}")
        
        if report.column_drifts:
            print(f"\nMetric Drifts:")
            for drift in report.column_drifts:
                if drift.drift_detected:
                    print(f"  [{drift.drift_severity.upper()}] {drift.column_name}.{drift.metric_name}")
                    print(f"    Baseline: {drift.baseline_value:.2f}")
                    print(f"    Current: {drift.current_value:.2f}")
                    if drift.change_percent is not None:
                        print(f"    Change: {drift.change_percent:+.2f}%")
        
        # Output to file
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump(report.to_dict(), f, indent=2)
            logger.info(f"Report saved to: {args.output}")
        
        # Return error code if critical drift detected
        if report.summary['has_critical_drift'] and args.fail_on_drift:
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
        output_format = args.output if hasattr(args, 'output') else 'text'
        verbose = args.verbose if hasattr(args, 'verbose') else False
        
        print_plan(plan, format=output_format, verbose=verbose)
        
        return 0
    
    except FileNotFoundError as e:
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='ProfileMesh - Data profiling and drift detection'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Plan command
    plan_parser = subparsers.add_parser('plan', help='Build and display profiling execution plan')
    plan_parser.add_argument(
        '--config', '-c',
        required=True,
        help='Path to configuration file (YAML or JSON)'
    )
    plan_parser.add_argument(
        '--output', '-o',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    plan_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose details including metrics and configuration'
    )
    
    # Profile command
    profile_parser = subparsers.add_parser('profile', help='Profile datasets')
    profile_parser.add_argument(
        '--config', '-c',
        required=True,
        help='Path to configuration file (YAML or JSON)'
    )
    profile_parser.add_argument(
        '--output', '-o',
        help='Output file for results (JSON)'
    )
    profile_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run profiling without writing to storage'
    )
    
    # Drift command
    drift_parser = subparsers.add_parser('drift', help='Detect drift between runs')
    drift_parser.add_argument(
        '--config', '-c',
        required=True,
        help='Path to configuration file (YAML or JSON)'
    )
    drift_parser.add_argument(
        '--dataset', '-d',
        required=True,
        help='Dataset name to check for drift'
    )
    drift_parser.add_argument(
        '--baseline', '-b',
        help='Baseline run ID (default: second-latest)'
    )
    drift_parser.add_argument(
        '--current',
        help='Current run ID (default: latest)'
    )
    drift_parser.add_argument(
        '--schema', '-s',
        help='Schema name'
    )
    drift_parser.add_argument(
        '--output', '-o',
        help='Output file for report (JSON)'
    )
    drift_parser.add_argument(
        '--fail-on-drift',
        action='store_true',
        help='Exit with error code if critical drift detected'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == 'plan':
        return plan_command(args)
    elif args.command == 'profile':
        return profile_command(args)
    elif args.command == 'drift':
        return drift_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())


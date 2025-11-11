"""
Command-line interface for ProfileMesh.

Provides CLI commands for profiling tables and detecting drift.
"""

import sys
import argparse
import logging
import json
from pathlib import Path
from typing import Optional

from .config.loader import ConfigLoader
from .config.schema import ProfileMeshConfig
from .profiling.core import ProfileEngine
from .storage.writer import ResultWriter
from .drift.detector import DriftDetector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def profile_command(args):
    """Execute profiling command."""
    logger.info(f"Loading configuration from: {args.config}")
    
    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)
        logger.info(f"Configuration loaded for environment: {config.environment}")
        
        # Create profiling engine
        engine = ProfileEngine(config)
        
        # Run profiling
        logger.info("Starting profiling...")
        results = engine.profile()
        
        if not results:
            logger.warning("No profiling results generated")
            return 1
        
        logger.info(f"Profiling completed: {len(results)} tables profiled")
        
        # Write results to storage
        if not args.dry_run:
            logger.info("Writing results to storage...")
            writer = ResultWriter(config.storage)
            writer.write_results(results, environment=config.environment)
            logger.info("Results written successfully")
            writer.close()
        else:
            logger.info("Dry run - results not written to storage")
        
        # Output results
        if args.output:
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump([r.to_dict() for r in results], f, indent=2)
            logger.info(f"Results saved to: {args.output}")
        
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
        logger.error(f"Profiling failed: {e}", exc_info=True)
        return 1


def drift_command(args):
    """Execute drift detection command."""
    logger.info(f"Loading configuration from: {args.config}")
    
    try:
        # Load configuration
        config = ConfigLoader.load_from_file(args.config)
        
        # Create drift detector
        detector = DriftDetector(config.storage)
        
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='ProfileMesh - Data profiling and drift detection'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
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
    if args.command == 'profile':
        return profile_command(args)
    elif args.command == 'drift':
        return drift_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())


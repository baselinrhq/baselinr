#!/usr/bin/env python3
"""
Baselinr drift detection script for dbt tests.

This script can be called from dbt tests to check for data drift.
Uses the latest profiling run for the table.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

try:
    from baselinr import BaselinrClient
    from baselinr.config.loader import ConfigLoader
except ImportError:
    print("ERROR: baselinr package not installed. Install with: pip install baselinr", file=sys.stderr)
    sys.exit(1)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.
    
    Args:
        base: Base dictionary
        override: Dictionary to merge on top of base
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description="Check for data drift using baselinr")
    parser.add_argument("--schema", required=True, help="Schema name")
    parser.add_argument("--table", required=True, help="Table name")
    parser.add_argument("--config", help="Path to baselinr config file (for connection/storage settings)")
    parser.add_argument("--drift-config", help="JSON string of drift_detection config to override base config")
    parser.add_argument("--run-id", help="Specific run_id to check (default: uses latest run)")

    args = parser.parse_args()

    try:
        # Load base config (connection/storage settings)
        base_config_dict: Dict[str, Any] = {}
        
        if args.config:
            # Load from specified config file
            base_config = ConfigLoader.load_from_file(args.config)
            # Convert to dict (handles both Pydantic v1 and v2)
            if hasattr(base_config, 'model_dump'):
                base_config_dict = base_config.model_dump()
            else:
                base_config_dict = base_config.dict()
        else:
            # Try to find config in common locations
            config_paths = [
                Path("baselinr_config.yml"),
                Path("baselinr_config.yaml"),
                Path("config.yml"),
                Path("config.yaml"),
            ]
            config_path = None
            for path in config_paths:
                if path.exists():
                    config_path = str(path)
                    break

            if config_path:
                base_config = ConfigLoader.load_from_file(config_path)
                # Convert to dict (handles both Pydantic v1 and v2)
                if hasattr(base_config, 'model_dump'):
                    base_config_dict = base_config.model_dump()
                else:
                    base_config_dict = base_config.dict()
            else:
                # No config file found - try to use minimal config from env vars
                # At minimum, we need storage connection info
                # For now, raise an error if no config found
                raise ValueError(
                    "No baselinr config file found. Please provide --config or create "
                    "a baselinr_config.yml file with at least storage connection settings."
                )

        # Merge drift_detection config if provided
        if args.drift_config:
            try:
                drift_config_override = json.loads(args.drift_config)
                if "drift_detection" not in base_config_dict:
                    base_config_dict["drift_detection"] = {}
                base_config_dict["drift_detection"] = deep_merge(
                    base_config_dict.get("drift_detection", {}),
                    drift_config_override
                )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in --drift-config: {e}")

        # Initialize client with merged config
        client = BaselinrClient(config=base_config_dict)

        # Detect drift (uses latest run if run_id not specified)
        print(
            f"Checking drift for {args.schema}.{args.table}...",
            file=sys.stderr
        )
        
        # Use latest run (current_run_id=None means use latest)
        report = client.detect_drift(
            args.table,
            schema_name=args.schema,
            current_run_id=args.run_id,  # None = use latest
        )

        # Check if any drift was detected
        drift_found = False
        drift_details = []
        
        for drift in report.column_drifts:
            if drift.drift_detected:
                drift_found = True
                drift_details.append(
                    f"{drift.column_name}.{drift.metric_name}: "
                    f"{drift.change_percent:.2f}% change "
                    f"(severity: {drift.drift_severity})"
                )

        if drift_found:
            print(
                f"FAIL: Drift detected for {args.schema}.{args.table}",
                file=sys.stderr
            )
            for detail in drift_details:
                print(f"  - {detail}", file=sys.stderr)
            sys.exit(1)
        else:
            print(
                f"PASS: No drift detected for {args.schema}.{args.table}",
                file=sys.stderr
            )
            sys.exit(0)

    except Exception as e:
        print(
            f"ERROR: Failed to check drift for {args.schema}.{args.table}: {e}",
            file=sys.stderr
        )
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

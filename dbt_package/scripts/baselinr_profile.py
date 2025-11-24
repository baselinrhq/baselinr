#!/usr/bin/env python3
"""
Baselinr profiling script for dbt post-hooks.

This script can be called from dbt post-hooks to profile tables after model execution.
Runs synchronously to ensure results are available before tests execute.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from baselinr import BaselinrClient
    from baselinr.config.loader import ConfigLoader
    from baselinr.baselinr.config.schema import TablePattern, PartitionConfig, SamplingConfig
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
    parser = argparse.ArgumentParser(description="Profile a table using baselinr")
    parser.add_argument("--schema", required=True, help="Schema name")
    parser.add_argument("--table", required=True, help="Table name")
    parser.add_argument("--config", help="Path to baselinr config file (for connection/storage settings)")
    parser.add_argument("--profiling-config", help="JSON string of profiling config to override base config")
    parser.add_argument("--output-run-id", action="store_true", help="Output run_id to stdout for drift tests")

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

        # Parse profiling config override
        profiling_config_override: Optional[Dict[str, Any]] = None
        partition_config: Optional[Dict[str, Any]] = None
        sampling_config: Optional[Dict[str, Any]] = None
        
        if args.profiling_config:
            try:
                profiling_config_override = json.loads(args.profiling_config)
                
                # Extract partition and sampling (these go into TablePattern, not ProfilingConfig)
                partition_config = profiling_config_override.pop("partition", None)
                sampling_config = profiling_config_override.pop("sampling", None)
                
                # Merge remaining profiling settings with base config
                if profiling_config_override:
                    if "profiling" not in base_config_dict:
                        base_config_dict["profiling"] = {}
                    base_config_dict["profiling"] = deep_merge(
                        base_config_dict.get("profiling", {}),
                        profiling_config_override
                    )
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in --profiling-config: {e}")

        # Initialize client with merged config
        client = BaselinrClient(config=base_config_dict)

        # Create table pattern with partition/sampling if provided
        pattern_dict: Dict[str, Any] = {
            "schema": args.schema,
            "table": args.table,
        }
        
        if partition_config:
            pattern_dict["partition"] = partition_config
        
        if sampling_config:
            pattern_dict["sampling"] = sampling_config
        
        pattern = TablePattern(**pattern_dict)

        # Profile the table (synchronous - blocks until complete)
        print(f"Profiling {args.schema}.{args.table}...", file=sys.stderr)
        results = client.profile(table_patterns=[pattern])

        if results:
            result = results[0]
            run_id = result.run_id
            
            print(
                f"SUCCESS: Profiled {args.schema}.{args.table} with {len(result.columns)} columns (run_id: {run_id})",
                file=sys.stderr
            )
            
            # Output run_id if requested (for drift tests to use)
            if args.output_run_id:
                print(run_id, file=sys.stdout)
            
            sys.exit(0)
        else:
            print(f"WARNING: No profiling results for {args.schema}.{args.table}", file=sys.stderr)
            sys.exit(0)

    except Exception as e:
        print(f"ERROR: Failed to profile {args.schema}.{args.table}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

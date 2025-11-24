#!/usr/bin/env python3
"""
Local test script for dbt integration.
Run this after setting up a test dbt project and compiling it.
"""

import json
import sys
from pathlib import Path

try:
    from baselinr.integrations.dbt import DBTManifestParser
except ImportError:
    print("ERROR: baselinr package not installed. Install with: pip install -e ..", file=sys.stderr)
    sys.exit(1)


def main():
    # Default to the test project created by test_local.sh or test_local.ps1
    import tempfile
    import os
    
    # Try Windows temp path first, then Unix
    if os.name == 'nt':  # Windows
        default_path = Path(tempfile.gettempdir()) / "test_dbt_project_local" / "target" / "manifest.json"
    else:
        default_path = Path("/tmp/test_dbt_project_local/target/manifest.json")
    
    manifest_path = default_path
    
    if len(sys.argv) > 1:
        manifest_path = Path(sys.argv[1])
    
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}", file=sys.stderr)
        print(f"Create a test dbt project and run 'dbt compile' first.", file=sys.stderr)
        print(f"\nAlternatively, if you have a manifest.json from another dbt project, you can test with:")
        print(f"  python test_local.py <path-to-manifest.json>", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading manifest from: {manifest_path}")
    
    parser = DBTManifestParser(manifest_path=str(manifest_path))
    manifest = parser.load_manifest()
    
    # Debug: Show all models and their tag structure
    all_models = parser.get_all_models()
    print(f"\nFound {len(all_models)} total models\n")
    
    for model in all_models:
        name = model.get("name")
        tags = model.get("tags", [])
        config = model.get("config", {})
        config_tags = config.get("tags", [])
        
        print(f"Model: {name}")
        print(f"  - node.tags: {tags} (type: {type(tags)})")
        print(f"  - node.config: {config}")
        print(f"  - node.config.tags: {config_tags} (type: {type(config_tags)})")
        
        # Check all possible tag locations
        if "tags" in model:
            print(f"  - Direct 'tags' key: {model['tags']}")
        if "config" in model and "tags" in model["config"]:
            print(f"  - config.tags key: {model['config']['tags']}")
        
        print()
    
    # Test get_models_by_tag
    print("Testing get_models_by_tag('critical'):")
    models = parser.get_models_by_tag('critical')
    print(f"Found {len(models)} models with 'critical' tag")
    for model in models:
        print(f"  - {model.get('name')}")
    
    # Test resolve_ref
    print("\nTesting resolve_ref('customers'):")
    try:
        schema, table = parser.resolve_ref('customers')
        print(f"  Schema: {schema}, Table: {table}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    # Test selector resolution
    print("\nTesting selector resolution:")
    from baselinr.integrations.dbt import DBTSelectorResolver
    resolver = DBTSelectorResolver(parser)
    
    try:
        models = resolver.resolve_selector('tag:critical')
        print(f"  tag:critical -> {len(models)} models")
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()


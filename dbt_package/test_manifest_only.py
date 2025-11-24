#!/usr/bin/env python3
"""
Test script that works with an existing dbt manifest.json file.
Use this if you have a manifest.json from a dbt project already.
"""

import json
import sys
from pathlib import Path

try:
    from baselinr.integrations.dbt import DBTManifestParser, DBTSelectorResolver
except ImportError:
    print("ERROR: baselinr package not installed. Install with: pip install -e ..", file=sys.stderr)
    sys.exit(1)


def inspect_manifest_structure(manifest_path: Path):
    """Inspect the raw manifest structure to see where tags are stored."""
    print(f"\n{'='*60}")
    print("Inspecting manifest structure...")
    print(f"{'='*60}\n")
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    nodes = manifest.get("nodes", {})
    models = [node for node in nodes.values() if node.get("resource_type") == "model"]
    
    print(f"Found {len(models)} models in manifest\n")
    
    for model in models[:3]:  # Show first 3 models
        name = model.get("name")
        print(f"Model: {name}")
        print(f"  Keys in node: {list(model.keys())[:10]}...")  # First 10 keys
        
        # Check for tags in various locations
        if "tags" in model:
            print(f"  ✓ Has 'tags' key: {model['tags']} (type: {type(model['tags'])})")
        else:
            print(f"  ✗ No 'tags' key")
        
        if "config" in model:
            config = model["config"]
            if isinstance(config, dict):
                print(f"  ✓ Has 'config' key (type: dict)")
                if "tags" in config:
                    print(f"    ✓ config.tags: {config['tags']} (type: {type(config['tags'])})")
                else:
                    print(f"    ✗ No 'tags' in config")
                print(f"    Config keys: {list(config.keys())[:10]}")
            else:
                print(f"  ✓ Has 'config' key (type: {type(config)})")
        else:
            print(f"  ✗ No 'config' key")
        
        # Check for tags in metadata or other locations
        if "meta" in model:
            print(f"  ✓ Has 'meta' key")
        if "patch_path" in model:
            print(f"  ✓ Has 'patch_path' key")
        
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_manifest_only.py <path-to-manifest.json>", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  python test_manifest_only.py /path/to/dbt/project/target/manifest.json", file=sys.stderr)
        sys.exit(1)
    
    manifest_path = Path(sys.argv[1])
    
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading manifest from: {manifest_path}")
    
    # First, inspect the raw structure
    inspect_manifest_structure(manifest_path)
    
    # Then test with our parser
    print(f"\n{'='*60}")
    print("Testing with DBTManifestParser...")
    print(f"{'='*60}\n")
    
    parser = DBTManifestParser(manifest_path=str(manifest_path))
    manifest = parser.load_manifest()
    
    # Debug: Show all models and their tag structure
    all_models = parser.get_all_models()
    print(f"Found {len(all_models)} total models\n")
    
    for model in all_models:
        name = model.get("name")
        tags = model.get("tags", [])
        config = model.get("config", {})
        config_tags = config.get("tags", []) if isinstance(config, dict) else []
        
        print(f"Model: {name}")
        print(f"  - node.tags: {tags} (type: {type(tags)})")
        print(f"  - node.config: {config}")
        print(f"  - node.config.tags: {config_tags} (type: {type(config_tags)})")
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
    resolver = DBTSelectorResolver(parser)
    
    try:
        models = resolver.resolve_selector('tag:critical')
        print(f"  tag:critical -> {len(models)} models")
        for model in models:
            print(f"    - {model.get('name')}")
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()


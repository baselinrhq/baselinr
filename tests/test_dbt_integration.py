"""
Integration tests for dbt integration.
"""

import json
import tempfile
from pathlib import Path

import pytest

from baselinr.config.schema import TablePattern
from baselinr.integrations.dbt import DBTManifestParser, DBTSelectorResolver
from baselinr.planner import PlanBuilder


@pytest.fixture
def sample_manifest():
    """Create a sample dbt manifest for testing."""
    return {
        "nodes": {
            "model.project.customers": {
                "resource_type": "model",
                "name": "customers",
                "package_name": "project",
                "schema": "analytics",
                "alias": "customers",
                "tags": ["critical", "customer"],
                "config": {"materialized": "table"},
                "original_file_path": "models/staging/customers.sql",
                "unique_id": "model.project.customers",
            },
            "model.project.orders": {
                "resource_type": "model",
                "name": "orders",
                "package_name": "project",
                "schema": "analytics",
                "alias": "orders",
                "tags": ["critical"],
                "config": {"materialized": "table"},
                "original_file_path": "models/staging/orders.sql",
                "unique_id": "model.project.orders",
            },
            "model.project.users": {
                "resource_type": "model",
                "name": "users",
                "package_name": "project",
                "schema": "analytics",
                "alias": "users",
                "tags": ["user"],
                "config": {"materialized": "view"},
                "original_file_path": "models/marts/users.sql",
                "unique_id": "model.project.users",
            },
        }
    }


@pytest.fixture
def manifest_file(sample_manifest, tmp_path):
    """Create a temporary manifest.json file."""
    manifest_path = tmp_path / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(sample_manifest, f)
    return str(manifest_path)


class TestDBTManifestParser:
    """Test dbt manifest parser."""

    def test_load_manifest(self, manifest_file):
        """Test loading manifest from file."""
        parser = DBTManifestParser(manifest_path=manifest_file)
        manifest = parser.load_manifest()

        assert manifest is not None
        assert "nodes" in manifest
        assert len(manifest["nodes"]) == 3

    def test_resolve_ref(self, manifest_file):
        """Test resolving dbt ref to table."""
        parser = DBTManifestParser(manifest_path=manifest_file)
        parser.load_manifest()

        schema, table = parser.resolve_ref("customers")
        assert schema == "analytics"
        assert table == "customers"

    def test_get_models_by_tag(self, manifest_file):
        """Test getting models by tag."""
        parser = DBTManifestParser(manifest_path=manifest_file)
        parser.load_manifest()

        models = parser.get_models_by_tag("critical")
        assert len(models) == 2
        assert all("critical" in m.get("tags", []) for m in models)

    def test_model_to_table(self, manifest_file):
        """Test converting model to table tuple."""
        parser = DBTManifestParser(manifest_path=manifest_file)
        parser.load_manifest()

        model = parser.get_model_by_name("customers")
        assert model is not None

        schema, table = parser.model_to_table(model)
        assert schema == "analytics"
        assert table == "customers"


class TestDBTSelectorResolver:
    """Test dbt selector resolver."""

    def test_resolve_tag_selector(self, manifest_file):
        """Test resolving tag selector."""
        parser = DBTManifestParser(manifest_path=manifest_file)
        parser.load_manifest()

        resolver = DBTSelectorResolver(parser)
        models = resolver.resolve_selector("tag:critical")

        assert len(models) == 2
        model_names = {m.get("name") for m in models}
        assert model_names == {"customers", "orders"}

    def test_resolve_config_selector(self, manifest_file):
        """Test resolving config selector."""
        parser = DBTManifestParser(manifest_path=manifest_file)
        parser.load_manifest()

        resolver = DBTSelectorResolver(parser)
        models = resolver.resolve_selector("config.materialized:table")

        assert len(models) == 2
        model_names = {m.get("name") for m in models}
        assert model_names == {"customers", "orders"}

    def test_resolve_name_selector(self, manifest_file):
        """Test resolving name selector."""
        parser = DBTManifestParser(manifest_path=manifest_file)
        parser.load_manifest()

        resolver = DBTSelectorResolver(parser)
        models = resolver.resolve_selector("name:customers")

        assert len(models) == 1
        assert models[0].get("name") == "customers"

    def test_resolve_union_selector(self, manifest_file):
        """Test resolving union selector (+)."""
        parser = DBTManifestParser(manifest_path=manifest_file)
        parser.load_manifest()

        resolver = DBTSelectorResolver(parser)
        models = resolver.resolve_selector("tag:critical+tag:user")

        assert len(models) == 3
        model_names = {m.get("name") for m in models}
        assert model_names == {"customers", "orders", "users"}

    def test_resolve_intersection_selector(self, manifest_file):
        """Test resolving intersection selector (,)."""
        parser = DBTManifestParser(manifest_path=manifest_file)
        parser.load_manifest()

        resolver = DBTSelectorResolver(parser)
        models = resolver.resolve_selector("tag:critical,config.materialized:table")

        assert len(models) == 2
        model_names = {m.get("name") for m in models}
        assert model_names == {"customers", "orders"}


class TestDBTTablePattern:
    """Test dbt table patterns in config."""

    def test_dbt_ref_pattern(self, manifest_file):
        """Test dbt_ref pattern."""
        pattern = TablePattern(
            dbt_ref="customers",
            dbt_manifest_path=manifest_file,
        )

        assert pattern.dbt_ref == "customers"
        assert pattern.dbt_manifest_path == manifest_file

    def test_dbt_selector_pattern(self, manifest_file):
        """Test dbt_selector pattern."""
        pattern = TablePattern(
            dbt_selector="tag:critical",
            dbt_manifest_path=manifest_file,
        )

        assert pattern.dbt_selector == "tag:critical"
        assert pattern.dbt_manifest_path == manifest_file

    def test_pattern_validation(self):
        """Test that only one selection method can be used."""
        # Should fail - multiple selection methods
        with pytest.raises(ValueError):
            TablePattern(
                table="customers",
                dbt_ref="customers",
            )

        # Should fail - no selection method
        with pytest.raises(ValueError):
            TablePattern(schema="analytics")


@pytest.mark.skip(reason="Requires full baselinr config and database connection")
class TestDBTPlanBuilder:
    """Test dbt pattern expansion in PlanBuilder."""

    def test_expand_dbt_ref(self, manifest_file):
        """Test expanding dbt_ref pattern."""
        # This would require a full BaselinrConfig with database connection
        # For now, we'll skip this test
        pass

    def test_expand_dbt_selector(self, manifest_file):
        """Test expanding dbt_selector pattern."""
        # This would require a full BaselinrConfig with database connection
        # For now, we'll skip this test
        pass


"""
Tests for ODCS (Open Data Contract Standard) implementation.
"""

import os
import tempfile
from pathlib import Path

import pytest

from baselinr.contracts import (
    ContractLoader,
    ContractLoadError,
    ODCSAdapter,
    ODCSColumn,
    ODCSContract,
    ODCSDataset,
    ODCSInfo,
    ODCSQuality,
    ODCSServiceLevel,
    ODCSValidator,
)

# =============================================================================
# ODCS Schema Tests
# =============================================================================


class TestODCSContract:
    """Tests for ODCSContract schema model."""

    def test_create_minimal_contract(self):
        """Test creating a minimal valid contract."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
        )
        assert contract.kind == "DataContract"
        assert contract.apiVersion == "v3.1.0"
        assert contract.status == "active"  # Default

    def test_create_full_contract(self):
        """Test creating a contract with all fields."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
            id="test-contract",
            version="1.0.0",
            status="active",
            info=ODCSInfo(
                title="Test Contract",
                description="A test contract",
                owner="test@example.com",
                domain="testing",
            ),
            dataset=[
                ODCSDataset(
                    name="test_table",
                    physicalName="public.test_table",
                    type="table",
                    columns=[
                        ODCSColumn(
                            name="id",
                            logicalType="integer",
                            isPrimaryKey=True,
                            isNullable=False,
                        ),
                        ODCSColumn(
                            name="email",
                            logicalType="string",
                            classification="pii",
                        ),
                    ],
                )
            ],
            quality=[
                ODCSQuality(
                    type="validity",
                    dimension="completeness",
                    rule="not_null",
                    column="id",
                    severity="error",
                )
            ],
            servicelevels=[
                ODCSServiceLevel(
                    property="freshness",
                    value=24,
                    unit="hours",
                )
            ],
        )

        assert contract.id == "test-contract"
        assert contract.info.title == "Test Contract"
        assert len(contract.dataset) == 1
        assert contract.dataset[0].name == "test_table"
        assert len(contract.dataset[0].columns) == 2
        assert contract.dataset[0].columns[0].isPrimaryKey is True

    def test_invalid_kind_raises_error(self):
        """Test that invalid kind raises validation error."""
        with pytest.raises(ValueError):
            ODCSContract(
                kind="InvalidKind",
                apiVersion="v3.1.0",
            )

    def test_get_dataset_names(self):
        """Test getting dataset names from contract."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
            dataset=[
                ODCSDataset(name="table1"),
                ODCSDataset(name="table2"),
            ],
        )
        names = contract.get_dataset_names()
        assert names == ["table1", "table2"]

    def test_get_all_quality_rules(self):
        """Test getting all quality rules from contract."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
            quality=[
                ODCSQuality(type="check1"),
            ],
            dataset=[
                ODCSDataset(
                    name="table1",
                    quality=[
                        ODCSQuality(type="check2"),
                    ],
                ),
            ],
        )
        rules = contract.get_all_quality_rules()
        assert len(rules) == 2


# =============================================================================
# Contract Loader Tests
# =============================================================================


class TestContractLoader:
    """Tests for ContractLoader."""

    def test_load_from_file(self):
        """Test loading a contract from a YAML file."""
        contract_content = """
kind: DataContract
apiVersion: v3.1.0
id: test-contract
info:
  title: Test Contract
dataset:
  - name: test_table
    columns:
      - name: id
        logicalType: integer
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".odcs.yaml",
            delete=False,
        ) as f:
            f.write(contract_content)
            f.flush()

            loader = ContractLoader(validate_on_load=False)
            contract = loader.load_from_file(f.name)

            assert contract.id == "test-contract"
            assert contract.info.title == "Test Contract"
            assert len(contract.dataset) == 1

        os.unlink(f.name)

    def test_load_from_directory(self):
        """Test loading contracts from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two contract files
            for i in range(2):
                contract_content = f"""
kind: DataContract
apiVersion: v3.1.0
id: contract-{i}
dataset:
  - name: table_{i}
"""
                filepath = Path(tmpdir) / f"contract_{i}.odcs.yaml"
                filepath.write_text(contract_content)

            loader = ContractLoader(validate_on_load=False)
            contracts = loader.load_from_directory(tmpdir)

            assert len(contracts) == 2
            ids = {c.id for c in contracts}
            assert ids == {"contract-0", "contract-1"}

    def test_load_nonexistent_file_raises_error(self):
        """Test that loading nonexistent file raises error."""
        loader = ContractLoader()
        with pytest.raises(ContractLoadError):
            loader.load_from_file("/nonexistent/path.odcs.yaml")

    def test_load_invalid_yaml_raises_error(self):
        """Test that loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".odcs.yaml",
            delete=False,
        ) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            loader = ContractLoader(validate_on_load=False)
            with pytest.raises(ContractLoadError):
                loader.load_from_file(f.name)

        os.unlink(f.name)


# =============================================================================
# Validator Tests
# =============================================================================


class TestODCSValidator:
    """Tests for ODCSValidator."""

    def test_validate_valid_contract(self):
        """Test validating a valid contract."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
            id="test-contract",
            info=ODCSInfo(title="Test Contract"),
            dataset=[
                ODCSDataset(
                    name="test_table",
                    columns=[ODCSColumn(name="id")],
                )
            ],
        )

        validator = ODCSValidator()
        result = validator.validate_full(contract)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_missing_kind(self):
        """Test validation fails with invalid kind."""
        # Create contract with wrong kind (would be caught by Pydantic first)
        contract = ODCSContract(
            kind="DataContract",  # Valid
            apiVersion="v3.1.0",
        )
        # Manually override for test
        contract.kind = ""

        validator = ODCSValidator()
        result = validator.validate_full(contract)

        assert result.valid is False
        assert any("kind" in str(e) for e in result.errors)

    def test_validate_warns_on_missing_datasets(self):
        """Test validation warns when no datasets defined."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
            id="test",
        )

        validator = ODCSValidator()
        result = validator.validate_full(contract)

        assert any("datasets" in str(w).lower() for w in result.warnings)

    def test_strict_mode_fails_on_warnings(self):
        """Test strict mode treats warnings as errors."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
        )  # Missing recommended fields

        validator = ODCSValidator(strict=True)
        result = validator.validate_full(contract)

        # With strict mode, warnings make it invalid
        assert result.valid is False


# =============================================================================
# Adapter Tests
# =============================================================================


class TestODCSAdapter:
    """Tests for ODCSAdapter."""

    def test_to_profiling_targets(self):
        """Test converting contract to profiling targets."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
            id="test",
            dataset=[
                ODCSDataset(
                    name="customers",
                    physicalName="public.customers",
                    columns=[
                        ODCSColumn(name="id", isPrimaryKey=True),
                        ODCSColumn(name="email"),
                    ],
                )
            ],
        )

        adapter = ODCSAdapter()
        targets = adapter.to_profiling_targets(contract)

        assert len(targets) == 1
        assert targets[0].table == "customers"
        assert targets[0].schema == "public"
        assert targets[0].columns == ["id", "email"]
        assert targets[0].primary_keys == ["id"]

    def test_to_validation_rules(self):
        """Test converting contract to validation rules."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
            id="test",
            dataset=[
                ODCSDataset(
                    name="customers",
                    columns=[
                        ODCSColumn(name="id", isPrimaryKey=True, isNullable=False),
                        ODCSColumn(name="email", isNullable=False),
                    ],
                )
            ],
            quality=[
                ODCSQuality(
                    type="validity",
                    rule="unique",
                    column="id",
                    severity="error",
                )
            ],
        )

        adapter = ODCSAdapter()
        rules = adapter.to_validation_rules(contract)

        # Should have: unique from quality, not_null from columns, unique from pk
        assert len(rules) >= 2

        rule_types = {r.type for r in rules}
        assert "unique" in rule_types
        assert "not_null" in rule_types

    def test_to_sla_configs(self):
        """Test converting contract to SLA configs."""
        contract = ODCSContract(
            kind="DataContract",
            apiVersion="v3.1.0",
            id="test",
            dataset=[ODCSDataset(name="customers")],
            servicelevels=[
                ODCSServiceLevel(property="freshness", value=24, unit="hours"),
                ODCSServiceLevel(property="availability", value=99.9, unit="percent"),
            ],
        )

        adapter = ODCSAdapter()
        configs = adapter.to_sla_configs(contract)

        assert len(configs) == 1
        assert configs[0].freshness_hours == 24
        assert configs[0].availability_percent == 99.9


# =============================================================================
# Integration Tests
# =============================================================================


class TestContractsIntegration:
    """Integration tests for the contracts module."""

    def test_full_workflow(self):
        """Test complete workflow: load -> validate -> adapt."""
        contract_content = """
kind: DataContract
apiVersion: v3.1.0
id: integration-test
info:
  title: Integration Test Contract
  owner: test@example.com
dataset:
  - name: users
    physicalName: public.users
    columns:
      - name: user_id
        logicalType: integer
        isPrimaryKey: true
        isNullable: false
      - name: email
        logicalType: string
        isNullable: false
        classification: pii
quality:
  - type: validity
    dimension: uniqueness
    specification:
      column: email
      rule: unique
    severity: error
servicelevels:
  - property: freshness
    value: 1
    unit: hours
"""
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".odcs.yaml",
            delete=False,
        ) as f:
            f.write(contract_content)
            f.flush()

            # Load
            loader = ContractLoader(validate_on_load=True)
            contract = loader.load_from_file(f.name)

            # Validate
            validator = ODCSValidator()
            result = validator.validate_full(contract)
            assert result.valid is True

            # Adapt
            adapter = ODCSAdapter()
            targets = adapter.to_profiling_targets(contract)
            rules = adapter.to_validation_rules(contract)
            slas = adapter.to_sla_configs(contract)

            assert len(targets) == 1
            assert len(rules) >= 2  # At least unique + not_null
            assert len(slas) == 1
            assert slas[0].freshness_hours == 1

        os.unlink(f.name)

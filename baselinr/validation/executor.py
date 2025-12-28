"""
Validation executor for Baselinr.

Orchestrates validation rule execution, stores results, and emits events.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from ..config.schema import BaselinrConfig, ValidationRuleConfig
from ..events import EventBus, ValidationFailed
from ..integrations.validation.base import ValidationResult, ValidationRule
from ..integrations.validation.registry import ValidationProviderRegistry

logger = logging.getLogger(__name__)


def _get_validation_table_sql(dialect: str) -> str:
    """Get SQL to create validation results table based on database dialect."""
    if dialect == "snowflake":
        return """
            CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                id INTEGER AUTOINCREMENT PRIMARY KEY,
                run_id VARCHAR(36) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                rule_type VARCHAR(50) NOT NULL,
                rule_config VARIANT,
                passed BOOLEAN NOT NULL,
                failure_reason TEXT,
                total_rows INTEGER,
                failed_rows INTEGER,
                failure_rate FLOAT,
                severity VARCHAR(20),
                validated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
                provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                metadata VARIANT
            )
        """
    elif dialect == "sqlite":
        return """
            CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id VARCHAR(36) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                rule_type VARCHAR(50) NOT NULL,
                rule_config TEXT,
                passed BOOLEAN NOT NULL,
                failure_reason TEXT,
                total_rows INTEGER,
                failed_rows INTEGER,
                failure_rate FLOAT,
                severity VARCHAR(20),
                validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                metadata TEXT
            )
        """
    else:
        # PostgreSQL, MySQL, etc.
        return """
            CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                run_id VARCHAR(36) NOT NULL,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(255),
                column_name VARCHAR(255),
                rule_type VARCHAR(50) NOT NULL,
                rule_config TEXT,
                passed BOOLEAN NOT NULL,
                failure_reason TEXT,
                total_rows INTEGER,
                failed_rows INTEGER,
                failure_rate FLOAT,
                severity VARCHAR(20),
                validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                metadata TEXT,
                INDEX idx_validation_run_id (run_id),
                INDEX idx_validation_table (table_name, schema_name),
                INDEX idx_validation_column (table_name, schema_name, column_name),
                INDEX idx_validation_validated_at (validated_at DESC)
            )
        """


class ValidationExecutor:
    """Executes validation rules and stores results."""

    def __init__(
        self,
        config: BaselinrConfig,
        source_engine: Engine,
        storage_engine: Engine,
        event_bus: Optional[EventBus] = None,
    ):
        """
        Initialize validation executor.

        Args:
            config: Baselinr configuration
            source_engine: SQLAlchemy engine for source database
            storage_engine: SQLAlchemy engine for storage database
            event_bus: Optional event bus for emitting validation events
        """
        self.config = config
        self.source_engine = source_engine
        self.storage_engine = storage_engine
        self.event_bus = event_bus

        # Ensure validation results table exists
        if config.storage.create_tables:
            self._ensure_validation_table()
        self.registry = ValidationProviderRegistry(config=config, source_engine=source_engine)

    def _ensure_validation_table(self) -> None:
        """Ensure validation results table exists in storage database."""
        try:
            dialect = self.storage_engine.dialect.name

            # Adjust SQL for PostgreSQL (uses SERIAL instead of AUTO_INCREMENT)
            if dialect == "postgresql":
                create_sql = """
                    CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                        id SERIAL PRIMARY KEY,
                        run_id VARCHAR(36) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        schema_name VARCHAR(255),
                        column_name VARCHAR(255),
                        rule_type VARCHAR(50) NOT NULL,
                        rule_config TEXT,
                        passed BOOLEAN NOT NULL,
                        failure_reason TEXT,
                        total_rows INTEGER,
                        failed_rows INTEGER,
                        failure_rate FLOAT,
                        severity VARCHAR(20),
                        validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                        metadata TEXT
                    )
                """
                # Create indexes separately for PostgreSQL
                index_sqls = [
                    "CREATE INDEX IF NOT EXISTS idx_validation_run_id "
                    "ON baselinr_validation_results (run_id)",
                    "CREATE INDEX IF NOT EXISTS idx_validation_table "
                    "ON baselinr_validation_results (table_name, schema_name)",
                    "CREATE INDEX IF NOT EXISTS idx_validation_column "
                    "ON baselinr_validation_results (table_name, schema_name, column_name)",
                    "CREATE INDEX IF NOT EXISTS idx_validation_validated_at "
                    "ON baselinr_validation_results (validated_at DESC)",
                ]
            elif dialect == "sqlite":
                create_sql = """
                    CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id VARCHAR(36) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        schema_name VARCHAR(255),
                        column_name VARCHAR(255),
                        rule_type VARCHAR(50) NOT NULL,
                        rule_config TEXT,
                        passed BOOLEAN NOT NULL,
                        failure_reason TEXT,
                        total_rows INTEGER,
                        failed_rows INTEGER,
                        failure_rate FLOAT,
                        severity VARCHAR(20),
                        validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                        metadata TEXT
                    )
                """
                index_sqls = [
                    "CREATE INDEX IF NOT EXISTS idx_validation_run_id "
                    "ON baselinr_validation_results (run_id)",
                    "CREATE INDEX IF NOT EXISTS idx_validation_table "
                    "ON baselinr_validation_results (table_name, schema_name)",
                    "CREATE INDEX IF NOT EXISTS idx_validation_column "
                    "ON baselinr_validation_results (table_name, schema_name, column_name)",
                    "CREATE INDEX IF NOT EXISTS idx_validation_validated_at "
                    "ON baselinr_validation_results (validated_at DESC)",
                ]
            elif dialect == "snowflake":
                create_sql = """
                    CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                        id INTEGER AUTOINCREMENT PRIMARY KEY,
                        run_id VARCHAR(36) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        schema_name VARCHAR(255),
                        column_name VARCHAR(255),
                        rule_type VARCHAR(50) NOT NULL,
                        rule_config VARIANT,
                        passed BOOLEAN NOT NULL,
                        failure_reason TEXT,
                        total_rows INTEGER,
                        failed_rows INTEGER,
                        failure_rate FLOAT,
                        severity VARCHAR(20),
                        validated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
                        provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                        metadata VARIANT
                    )
                """
                index_sqls = [
                    "CREATE INDEX IF NOT EXISTS idx_validation_run_id "
                    "ON baselinr_validation_results (run_id)",
                    "CREATE INDEX IF NOT EXISTS idx_validation_table "
                    "ON baselinr_validation_results (table_name, schema_name)",
                    "CREATE INDEX IF NOT EXISTS idx_validation_column "
                    "ON baselinr_validation_results (table_name, schema_name, column_name)",
                    "CREATE INDEX IF NOT EXISTS idx_validation_validated_at "
                    "ON baselinr_validation_results (validated_at DESC)",
                ]
            else:
                # MySQL, etc.
                create_sql = """
                    CREATE TABLE IF NOT EXISTS baselinr_validation_results (
                        id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        run_id VARCHAR(36) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        schema_name VARCHAR(255),
                        column_name VARCHAR(255),
                        rule_type VARCHAR(50) NOT NULL,
                        rule_config TEXT,
                        passed BOOLEAN NOT NULL,
                        failure_reason TEXT,
                        total_rows INTEGER,
                        failed_rows INTEGER,
                        failure_rate FLOAT,
                        severity VARCHAR(20),
                        validated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        provider VARCHAR(50) NOT NULL DEFAULT 'builtin',
                        metadata TEXT
                    )
                """
                index_sqls = [
                    "CREATE INDEX idx_validation_run_id " "ON baselinr_validation_results (run_id)",
                    "CREATE INDEX idx_validation_table "
                    "ON baselinr_validation_results (table_name, schema_name)",
                    "CREATE INDEX idx_validation_column "
                    "ON baselinr_validation_results (table_name, schema_name, column_name)",
                    "CREATE INDEX idx_validation_validated_at "
                    "ON baselinr_validation_results (validated_at DESC)",
                ]

            with self.storage_engine.connect() as conn:
                conn.execute(text(create_sql))
                for index_sql in index_sqls:
                    try:
                        conn.execute(text(index_sql))
                    except Exception:
                        # Index might already exist, ignore
                        pass
                conn.commit()
                logger.debug("Validation results table ensured")
        except Exception as e:
            logger.warning(f"Could not ensure validation results table: {e}")

    def _load_rules_from_config(self) -> List[ValidationRule]:
        """
        Load validation rules from configuration using ConfigMerger.

        Rules are loaded from ODCS contracts. Provider-level rules
        in validation.providers[] are still supported for provider configuration.

        Returns:
            List of ValidationRule objects
        """
        rules: List[ValidationRule] = []

        if not self.config.validation or not self.config.validation.enabled:
            return rules

        validation_config = self.config.validation

        # Load validation rules from ODCS contracts
        from ..contracts import ContractLoader, ODCSAdapter

        validation_rules = []
        if self.config.contracts:
            loader = ContractLoader(
                validate_on_load=self.config.contracts.validate_on_load,
                file_patterns=self.config.contracts.file_patterns,
            )
            try:
                contracts = loader.load_from_directory(
                    self.config.contracts.directory,
                    recursive=self.config.contracts.recursive,
                    exclude_patterns=self.config.contracts.exclude_patterns,
                )
                adapter = ODCSAdapter()
                for contract in contracts:
                    contract_rules = adapter.to_validation_rules(contract)
                    for adapter_rule in contract_rules:
                        if not adapter_rule.table:
                            # Skip rules without table (they need table context to be useful)
                            continue

                        # Use schema from rule or source config
                        rule_schema = self.config.source.schema_

                        validation_rule = ValidationRule(
                            rule_type=adapter_rule.type,
                            table=adapter_rule.table,
                            schema=rule_schema,
                            column=adapter_rule.column,
                            config={
                                "pattern": adapter_rule.pattern,
                                "min_value": adapter_rule.min_value,
                                "max_value": adapter_rule.max_value,
                                "allowed_values": adapter_rule.allowed_values,
                                "references": (
                                    {
                                        "table": adapter_rule.reference_table,
                                        "column": adapter_rule.reference_column,
                                    }
                                    if adapter_rule.reference_table
                                    else None
                                ),
                            },
                            severity=adapter_rule.severity,
                            enabled=adapter_rule.enabled,
                        )
                        validation_rules.append(validation_rule)
            except Exception as e:
                logger.warning(f"Failed to load validation rules from contracts: {e}")

        rules.extend(validation_rules)

        # Load rules from providers (provider-level rules are different from dataset rules)
        # These are for provider configuration (e.g., Great Expectations suite config)
        for provider_config in validation_config.providers:
            if not isinstance(provider_config, dict):
                continue

            provider_rules = provider_config.get("rules", [])

            for rule_config_dict in provider_rules:
                if not isinstance(rule_config_dict, dict):
                    continue

                # Convert dict to ValidationRuleConfig for validation
                try:
                    rule_config = ValidationRuleConfig(**rule_config_dict)
                except Exception as e:
                    logger.warning(f"Invalid validation rule config: {e}")
                    continue

                # Get table from rule config or provider config
                table = rule_config.table or provider_config.get("table")
                if not table:
                    logger.warning("Validation rule missing table name, skipping")
                    continue

                schema = provider_config.get("schema") or self.config.source.schema_

                rule = ValidationRule(
                    rule_type=rule_config.type,
                    table=table,
                    schema=schema,
                    column=rule_config.column,
                    config={
                        "pattern": rule_config.pattern,
                        "min_value": rule_config.min_value,
                        "max_value": rule_config.max_value,
                        "allowed_values": rule_config.allowed_values,
                        "references": rule_config.references,
                    },
                    severity=rule_config.severity,
                    enabled=rule_config.enabled,
                )
                rules.append(rule)

        return rules

    def _store_result(
        self, result: ValidationResult, run_id: str, provider_name: str = "builtin"
    ) -> None:
        """
        Store validation result in database.

        Args:
            result: ValidationResult to store
            run_id: Profiling run ID (or generate new one)
            provider_name: Name of the provider that executed the validation
        """
        try:
            with self.storage_engine.connect() as conn:
                # Serialize rule config to JSON
                rule_config_json = json.dumps(result.rule.config)
                metadata_json = json.dumps(result.metadata) if result.metadata else None

                insert_query = text(
                    """
                    INSERT INTO baselinr_validation_results (
                        run_id, table_name, schema_name, column_name, rule_type,
                        rule_config, passed, failure_reason, total_rows, failed_rows,
                        failure_rate, severity, validated_at, provider, metadata
                    ) VALUES (
                        :run_id, :table_name, :schema_name, :column_name, :rule_type,
                        :rule_config, :passed, :failure_reason, :total_rows, :failed_rows,
                        :failure_rate, :severity, :validated_at, :provider, :metadata
                    )
                """
                )

                conn.execute(
                    insert_query,
                    {
                        "run_id": run_id,
                        "table_name": result.rule.table,
                        "schema_name": result.rule.schema,
                        "column_name": result.rule.column,
                        "rule_type": result.rule.rule_type,
                        "rule_config": rule_config_json,
                        "passed": result.passed,
                        "failure_reason": result.failure_reason,
                        "total_rows": result.total_rows,
                        "failed_rows": result.failed_rows,
                        "failure_rate": result.failure_rate,
                        "severity": result.rule.severity,
                        "validated_at": datetime.utcnow(),
                        "provider": provider_name,
                        "metadata": metadata_json,
                    },
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing validation result: {e}", exc_info=True)

    def _emit_validation_event(self, result: ValidationResult) -> None:
        """
        Emit validation event if validation failed.

        Args:
            result: ValidationResult to check
        """
        if not self.event_bus or result.passed:
            return

        event = ValidationFailed(
            event_type="ValidationFailed",
            timestamp=datetime.utcnow(),
            table=result.rule.table,
            column=result.rule.column,
            rule_type=result.rule.rule_type,
            rule_config=result.rule.config,
            failure_reason=result.failure_reason or "Validation failed",
            sample_failures=result.sample_failures,
            severity=result.rule.severity,
            total_failures=result.failed_rows,
            total_rows=result.total_rows,
            failure_rate=result.failure_rate,
            metadata={},
        )

        self.event_bus.emit(event)

    def execute_validation(
        self, run_id: Optional[str] = None, table_filter: Optional[str] = None
    ) -> List[ValidationResult]:
        """
        Execute all validation rules.

        Args:
            run_id: Optional run ID to associate with validation results.
                   If None, generates a new UUID.
            table_filter: Optional table name to filter rules

        Returns:
            List of ValidationResult objects
        """
        if not self.config.validation or not self.config.validation.enabled:
            logger.info("Validation is disabled in configuration")
            return []

        if run_id is None:
            run_id = str(uuid.uuid4())

        rules = self._load_rules_from_config()

        if table_filter:
            rules = [r for r in rules if r.table == table_filter]

        if not rules:
            logger.info("No validation rules configured")
            return []

        logger.info(f"Executing {len(rules)} validation rules")

        # Execute validation rules
        results = self.registry.validate_rules(rules)

        # Store results and emit events
        for result in results:
            self._store_result(result, run_id, provider_name="builtin")
            self._emit_validation_event(result)

        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        logger.info(f"Validation complete: {passed_count} passed, {failed_count} failed")

        return results

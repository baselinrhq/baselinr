"""
Service layer for validation rules management operations.
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.engine import Engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validation rules management operations."""
    
    def __init__(self, db_engine: Optional[Engine] = None):
        """
        Initialize validation service.
        
        Args:
            db_engine: Database engine for rule storage
        """
        self.db_engine = db_engine
        self._ensure_table_exists()
    
    def _ensure_table_exists(self) -> None:
        """Ensure validation_rules table exists."""
        if not self.db_engine:
            logger.warning("No database engine provided, skipping table creation")
            return
        
        try:
            dialect = self.db_engine.dialect.name
            with self.db_engine.connect() as conn:
                # Check if table exists (database-specific)
                table_exists = False
                if dialect == "postgresql":
                    check_query = """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'baselinr_validation_rules'
                        )
                    """
                    result = conn.execute(text(check_query)).fetchone()
                    table_exists = result and result[0]
                elif dialect == "sqlite":
                    check_query = """
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='baselinr_validation_rules'
                    """
                    result = conn.execute(text(check_query)).fetchone()
                    table_exists = result is not None
                else:
                    # For other databases, try to create and catch error if exists
                    try:
                        # Try a simple query to see if table exists
                        conn.execute(text("SELECT 1 FROM baselinr_validation_rules LIMIT 1"))
                        table_exists = True
                    except Exception:
                        table_exists = False
                
                if not table_exists:
                    # Table doesn't exist, create it
                    # Use TEXT for SQLite, JSONB for PostgreSQL
                    config_type = "TEXT" if dialect == "sqlite" else "JSONB"
                    
                    create_query = f"""
                        CREATE TABLE IF NOT EXISTS baselinr_validation_rules (
                            id VARCHAR(255) PRIMARY KEY,
                            rule_type VARCHAR(50) NOT NULL,
                            table_name VARCHAR(255) NOT NULL,
                            schema_name VARCHAR(255),
                            column_name VARCHAR(255),
                            config {config_type} NOT NULL DEFAULT '{{}}',
                            severity VARCHAR(20) NOT NULL DEFAULT 'medium',
                            enabled BOOLEAN NOT NULL DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP,
                            last_tested TIMESTAMP,
                            last_test_result BOOLEAN
                        )
                    """
                    conn.execute(text(create_query))
                    
                    # Create indexes
                    indexes = [
                        "CREATE INDEX IF NOT EXISTS idx_validation_rules_table ON baselinr_validation_rules(table_name)",
                        "CREATE INDEX IF NOT EXISTS idx_validation_rules_schema ON baselinr_validation_rules(schema_name)",
                        "CREATE INDEX IF NOT EXISTS idx_validation_rules_type ON baselinr_validation_rules(rule_type)",
                        "CREATE INDEX IF NOT EXISTS idx_validation_rules_enabled ON baselinr_validation_rules(enabled)",
                    ]
                    for idx_query in indexes:
                        try:
                            conn.execute(text(idx_query))
                        except Exception as idx_error:
                            logger.warning(f"Failed to create index: {idx_error}")
                    
                    conn.commit()
                    logger.info("Created baselinr_validation_rules table")
        except Exception as e:
            logger.error(f"Failed to ensure validation_rules table exists: {e}")
            # Don't raise - allow service to work even if table creation fails
    
    def list_rules(
        self,
        table: Optional[str] = None,
        schema: Optional[str] = None,
        rule_type: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List validation rules with optional filters.
        
        Args:
            table: Filter by table name
            schema: Filter by schema name
            rule_type: Filter by rule type
            enabled: Filter by enabled status
            
        Returns:
            List of rule dictionaries
        """
        if not self.db_engine:
            return []
        
        try:
            with self.db_engine.connect() as conn:
                query = "SELECT * FROM baselinr_validation_rules WHERE 1=1"
                params = {}
                
                if table:
                    query += " AND table_name = :table"
                    params["table"] = table
                
                if schema:
                    query += " AND schema_name = :schema"
                    params["schema"] = schema
                
                if rule_type:
                    query += " AND rule_type = :rule_type"
                    params["rule_type"] = rule_type
                
                if enabled is not None:
                    query += " AND enabled = :enabled"
                    params["enabled"] = enabled
                
                query += " ORDER BY created_at DESC"
                
                rows = conn.execute(text(query), params).fetchall()
                
                rules = []
                for row in rows:
                    rule = {
                        "id": row[0],
                        "rule_type": row[1],
                        "table": row[2],
                        "schema": row[3],
                        "column": row[4],
                        "config": json.loads(row[5]) if isinstance(row[5], str) else row[5],
                        "severity": row[6],
                        "enabled": row[7],
                        "created_at": row[8],
                        "updated_at": row[9],
                        "last_tested": row[10],
                        "last_test_result": row[11],
                    }
                    rules.append(rule)
                
                return rules
        except Exception as e:
            # If table doesn't exist, return empty list
            if "no such table" in str(e).lower():
                logger.info("Validation rules table does not exist, returning empty list")
                return []
            logger.error(f"Failed to list validation rules: {e}")
            raise RuntimeError(f"Failed to list validation rules: {str(e)}")
    
    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific validation rule by ID.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            Rule dictionary or None if not found
        """
        if not self.db_engine:
            return None
        
        try:
            with self.db_engine.connect() as conn:
                query = "SELECT * FROM baselinr_validation_rules WHERE id = :id"
                row = conn.execute(text(query), {"id": rule_id}).fetchone()
                
                if not row:
                    return None
                
                return {
                    "id": row[0],
                    "rule_type": row[1],
                    "table": row[2],
                    "schema": row[3],
                    "column": row[4],
                    "config": json.loads(row[5]) if isinstance(row[5], str) else row[5],
                    "severity": row[6],
                    "enabled": row[7],
                    "created_at": row[8],
                    "updated_at": row[9],
                    "last_tested": row[10],
                    "last_test_result": row[11],
                }
        except Exception as e:
            logger.error(f"Failed to get validation rule: {e}")
            # Check if it's a "table doesn't exist" error - return None in that case
            if "no such table" in str(e).lower():
                return None
            raise RuntimeError(f"Failed to get validation rule: {str(e)}")
    
    def create_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new validation rule.
        
        Args:
            rule_data: Rule data dictionary
            
        Returns:
            Created rule dictionary
        """
        if not self.db_engine:
            raise RuntimeError("Database engine not available")
        
        rule_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        try:
            with self.db_engine.connect() as conn:
                insert_query = """
                    INSERT INTO baselinr_validation_rules 
                    (id, rule_type, table_name, schema_name, column_name, config, severity, enabled, created_at)
                    VALUES (:id, :rule_type, :table_name, :schema_name, :column_name, :config, :severity, :enabled, :created_at)
                """
                
                params = {
                    "id": rule_id,
                    "rule_type": rule_data["rule_type"],
                    "table_name": rule_data["table"],
                    "schema_name": rule_data.get("schema"),
                    "column_name": rule_data.get("column"),
                    "config": json.dumps(rule_data.get("config", {})),
                    "severity": rule_data.get("severity", "medium"),
                    "enabled": rule_data.get("enabled", True),
                    "created_at": now,
                }
                
                conn.execute(text(insert_query), params)
                conn.commit()
                
                # Return the created rule
                return self.get_rule(rule_id) or {}
        except Exception as e:
            logger.error(f"Failed to create validation rule: {e}")
            raise RuntimeError(f"Failed to create validation rule: {str(e)}")
    
    def update_rule(self, rule_id: str, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing validation rule.
        
        Args:
            rule_id: Rule identifier
            rule_data: Updated rule data (only provided fields will be updated)
            
        Returns:
            Updated rule dictionary
        """
        if not self.db_engine:
            raise RuntimeError("Database engine not available")
        
        # Check if rule exists
        existing = self.get_rule(rule_id)
        if not existing:
            raise ValueError(f"Validation rule not found: {rule_id}")
        
        now = datetime.now(timezone.utc)
        
        try:
            with self.db_engine.connect() as conn:
                # Build update query dynamically based on provided fields
                updates = []
                params = {"id": rule_id, "updated_at": now}
                
                if "rule_type" in rule_data:
                    updates.append("rule_type = :rule_type")
                    params["rule_type"] = rule_data["rule_type"]
                
                if "table" in rule_data:
                    updates.append("table_name = :table_name")
                    params["table_name"] = rule_data["table"]
                
                if "schema" in rule_data:
                    updates.append("schema_name = :schema_name")
                    params["schema_name"] = rule_data["schema"]
                
                if "column" in rule_data:
                    updates.append("column_name = :column_name")
                    params["column_name"] = rule_data["column"]
                
                if "config" in rule_data:
                    updates.append("config = :config")
                    params["config"] = json.dumps(rule_data["config"])
                
                if "severity" in rule_data:
                    updates.append("severity = :severity")
                    params["severity"] = rule_data["severity"]
                
                if "enabled" in rule_data:
                    updates.append("enabled = :enabled")
                    params["enabled"] = rule_data["enabled"]
                
                if not updates:
                    # No updates provided, return existing rule
                    return existing
                
                updates.append("updated_at = :updated_at")
                
                update_query = f"""
                    UPDATE baselinr_validation_rules 
                    SET {', '.join(updates)}
                    WHERE id = :id
                """
                
                conn.execute(text(update_query), params)
                conn.commit()
                
                # Return the updated rule
                return self.get_rule(rule_id) or {}
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update validation rule: {e}")
            raise RuntimeError(f"Failed to update validation rule: {str(e)}")
    
    def delete_rule(self, rule_id: str) -> bool:
        """
        Delete a validation rule.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            True if deleted, False if not found
        """
        if not self.db_engine:
            raise RuntimeError("Database engine not available")
        
        try:
            with self.db_engine.connect() as conn:
                delete_query = "DELETE FROM baselinr_validation_rules WHERE id = :id"
                result = conn.execute(text(delete_query), {"id": rule_id})
                conn.commit()
                
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete validation rule: {e}")
            # Check if it's a "table doesn't exist" error - return False in that case
            if "no such table" in str(e).lower():
                return False
            raise RuntimeError(f"Failed to delete validation rule: {str(e)}")
    
    def test_rule(self, rule_id: str) -> Dict[str, Any]:
        """
        Test a validation rule against the database.
        
        This is a simplified test that validates the rule structure.
        Full validation execution requires connection to the source database
        and should be done through the ValidationExecutor.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            Test result dictionary
        """
        rule = self.get_rule(rule_id)
        if not rule:
            raise ValueError(f"Validation rule not found: {rule_id}")
        
        now = datetime.now(timezone.utc)
        
        # For now, we'll do basic validation of the rule structure
        # Full testing requires database connection and ValidationExecutor
        # This is a placeholder that validates the rule configuration
        
        passed = True
        failure_reason = None
        
        # Basic validation checks
        if not rule.get("table"):
            passed = False
            failure_reason = "Table name is required"
        elif not rule.get("rule_type"):
            passed = False
            failure_reason = "Rule type is required"
        elif rule.get("rule_type") not in ["format", "range", "enum", "not_null", "unique", "referential"]:
            passed = False
            failure_reason = f"Invalid rule type: {rule.get('rule_type')}"
        elif rule.get("severity") not in ["low", "medium", "high"]:
            passed = False
            failure_reason = f"Invalid severity: {rule.get('severity')}"
        
        # Update last_tested and last_test_result
        try:
            if self.db_engine:
                with self.db_engine.connect() as conn:
                    update_query = """
                        UPDATE baselinr_validation_rules 
                        SET last_tested = :last_tested, last_test_result = :last_test_result
                        WHERE id = :id
                    """
                    conn.execute(text(update_query), {
                        "id": rule_id,
                        "last_tested": now,
                        "last_test_result": passed
                    })
                    conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update test result: {e}")
        
        return {
            "rule_id": rule_id,
            "passed": passed,
            "failure_reason": failure_reason,
            "total_rows": 0,  # Would require actual database connection
            "failed_rows": 0,
            "failure_rate": 0.0,
            "sample_failures": [],
            "tested_at": now,
        }


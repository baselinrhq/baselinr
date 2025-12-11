"""
Service layer for configuration management operations.
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.engine import Engine
from sqlalchemy import text

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from baselinr.config.loader import ConfigLoader
    from baselinr.config.schema import BaselinrConfig, ConnectionConfig
    from baselinr.connectors.factory import create_connector
    BASELINR_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Baselinr modules not available: {e}")
    BASELINR_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for configuration operations."""
    
    def __init__(self, db_engine: Optional[Engine] = None):
        """
        Initialize config service.
        
        Args:
            db_engine: Optional database engine for config history storage
        """
        self.db_engine = db_engine
        self._config_path = self._find_config_path()
    
    def _find_config_path(self) -> Optional[str]:
        """Find the config file path from environment or common locations."""
        config_path = os.getenv("BASELINR_CONFIG")
        
        if config_path and os.path.exists(config_path):
            return config_path
        
        # Try common locations
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(backend_dir, "../../"))
        
        possible_paths = [
            os.path.join(project_root, "examples", "config.yml"),
            os.path.join(project_root, "config.yml"),
            os.path.join(project_root, "baselinr", "examples", "config.yml"),
            "examples/config.yml",
            "config.yml",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found config file at: {path}")
                return path
        
        return None
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load current configuration from file or database.
        
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        if self._config_path:
            try:
                config = ConfigLoader.load_from_file(self._config_path)
                # Convert Pydantic model to dict
                return config.model_dump(exclude_none=True)
            except FileNotFoundError:
                logger.warning(f"Config file not found: {self._config_path}")
                raise
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                raise ValueError(f"Invalid configuration: {e}")
        
        # If no config file, return empty config structure
        return {}
    
    def save_config(self, config: Dict[str, Any], comment: Optional[str] = None, created_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Save configuration to file or database.
        
        Args:
            config: Configuration dictionary to save
            comment: Optional comment for this version
            created_by: Optional user identifier
            
        Returns:
            Saved configuration dictionary
            
        Raises:
            ValueError: If config is invalid
        """
        if not BASELINR_AVAILABLE:
            raise RuntimeError("Baselinr modules not available")
        
        # Validate config before saving
        try:
            validated_config = BaselinrConfig(**config)
        except Exception as e:
            logger.error(f"Config validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}")
        
        # Save to file
        if self._config_path:
            try:
                config_dict = validated_config.model_dump(exclude_none=True)
                
                # Filter out sensitive data before saving to file
                # API keys should be stored in environment variables, not in config files
                file_safe_config = self._sanitize_config_for_file(config_dict)
                
                # Write to file based on extension
                path = Path(self._config_path)
                with open(path, 'w') as f:
                    if path.suffix in ['.yaml', '.yml']:
                        yaml.dump(file_safe_config, f, default_flow_style=False, sort_keys=False)
                    elif path.suffix == '.json':
                        json.dump(file_safe_config, f, indent=2)
                    else:
                        # Default to YAML
                        yaml.dump(file_safe_config, f, default_flow_style=False, sort_keys=False)
                
                logger.info(f"Config saved to: {self._config_path} (sensitive data filtered)")
                
                # Save to history (with sanitized data)
                self._save_to_history(file_safe_config, comment=comment, created_by=created_by)
                
                return config_dict
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
                raise RuntimeError(f"Failed to save configuration: {e}")
        else:
            # If no config path, just return validated config
            logger.warning("No config file path configured, config not persisted")
            config_dict = validated_config.model_dump(exclude_none=True)
            
            # Still save to history even if no file path
            self._save_to_history(config_dict, comment=comment, created_by=created_by)
            
            return config_dict
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate configuration without saving.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not BASELINR_AVAILABLE:
            return False, ["Baselinr modules not available"]
        
        try:
            BaselinrConfig(**config)
            return True, []
        except Exception as e:
            errors = []
            if hasattr(e, 'errors'):
                # Pydantic validation errors
                for error in e.errors():
                    field = '.'.join(str(loc) for loc in error.get('loc', []))
                    msg = error.get('msg', 'Validation error')
                    errors.append(f"{field}: {msg}")
            else:
                errors.append(str(e))
            return False, errors
    
    def test_connection(self, connection: Dict[str, Any]) -> tuple[bool, str]:
        """
        Test database connection.
        
        Args:
            connection: Connection configuration dictionary
            
        Returns:
            Tuple of (success, message)
        """
        if not BASELINR_AVAILABLE:
            return False, "Baselinr modules not available"
        
        try:
            # Create ConnectionConfig from dict
            connection_config = ConnectionConfig(**connection)
            
            # Create connector and test connection
            connector = create_connector(connection_config)
            
            # Test connection with timeout
            with connector.engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            
            return True, "Connection successful"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Connection test failed: {error_msg}")
            return False, f"Connection failed: {error_msg}"
    
    def get_config_history(self) -> List[Dict[str, Any]]:
        """
        Get configuration version history.
        
        Returns:
            List of config version metadata
        """
        if not self.db_engine:
            return []
        
        try:
            with self.db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT version_id, created_at, created_by, comment
                    FROM baselinr_config_history
                    ORDER BY created_at DESC
                    LIMIT 50
                """))
                
                versions = []
                for row in result:
                    versions.append({
                        "version_id": row[0],
                        "created_at": row[1].isoformat() if isinstance(row[1], datetime) else str(row[1]),
                        "created_by": row[2],
                        "comment": row[3],
                    })
                
                return versions
        except Exception as e:
            logger.warning(f"Failed to get config history: {e}")
            return []
    
    def get_config_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific configuration version.
        
        Args:
            version_id: Version identifier
            
        Returns:
            Configuration dictionary for this version, or None if not found
        """
        if not self.db_engine:
            return None
        
        try:
            with self.db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT version_id, config_json, created_at, created_by, comment
                    FROM baselinr_config_history
                    WHERE version_id = :version_id
                """), {"version_id": version_id})
                
                row = result.fetchone()
                if not row:
                    return None
                
                return {
                    "version_id": row[0],
                    "config": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                    "created_at": row[2].isoformat() if isinstance(row[2], datetime) else str(row[2]),
                    "created_by": row[3],
                    "comment": row[4],
                }
        except Exception as e:
            logger.warning(f"Failed to get config version: {e}")
            return None
    
    def _deep_diff(self, old: Dict[str, Any], new: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """
        Calculate deep diff between two config dictionaries.
        
        Args:
            old: Old configuration
            new: New configuration
            path: Current path prefix for nested keys
            
        Returns:
            Dictionary with 'added', 'removed', and 'changed' keys
        """
        added = {}
        removed = {}
        changed = {}
        
        # Get all keys from both configs
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            old_val = old.get(key)
            new_val = new.get(key)
            
            if key not in old:
                # Added
                added[current_path] = new_val
            elif key not in new:
                # Removed
                removed[current_path] = old_val
            elif old_val != new_val:
                # Check if both are dicts for nested comparison
                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    nested_diff = self._deep_diff(old_val, new_val, current_path)
                    added.update(nested_diff.get('added', {}))
                    removed.update(nested_diff.get('removed', {}))
                    changed.update(nested_diff.get('changed', {}))
                elif isinstance(old_val, list) and isinstance(new_val, list):
                    # For arrays, just mark as changed
                    changed[current_path] = {"old": old_val, "new": new_val}
                else:
                    # Changed value
                    changed[current_path] = {"old": old_val, "new": new_val}
        
        return {
            "added": added,
            "removed": removed,
            "changed": changed
        }
    
    def get_config_diff(self, version_id: str, compare_with: Optional[str] = None) -> Dict[str, Any]:
        """
        Get diff between a version and current config or another version.
        
        Args:
            version_id: Version ID to compare
            compare_with: Version ID to compare with (None = current config)
            
        Returns:
            Dictionary with diff information
        """
        # Get the version config
        version_data = self.get_config_version(version_id)
        if not version_data:
            raise ValueError(f"Version not found: {version_id}")
        
        version_config = version_data["config"]
        
        # Get the config to compare with
        if compare_with:
            compare_data = self.get_config_version(compare_with)
            if not compare_data:
                raise ValueError(f"Compare version not found: {compare_with}")
            compare_config = compare_data["config"]
            compare_label = compare_with
        else:
            # Compare with current config
            compare_config = self.load_config()
            compare_label = "current"
        
        # Calculate diff
        diff = self._deep_diff(compare_config, version_config)
        
        return {
            "version_id": version_id,
            "compare_with": compare_label,
            "added": diff["added"],
            "removed": diff["removed"],
            "changed": diff["changed"]
        }
    
    def _sanitize_config_for_file(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive data from config before saving to file.
        
        API keys and other secrets should be stored in environment variables,
        not in config files that might be committed to version control.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Sanitized configuration with sensitive fields removed or replaced
        """
        sanitized = json.loads(json.dumps(config))  # Deep copy
        
        # Remove API keys from LLM config
        if 'llm' in sanitized and isinstance(sanitized['llm'], dict):
            if 'api_key' in sanitized['llm']:
                api_key = sanitized['llm']['api_key']
                # If it's an actual key (not an env var reference), remove it
                if isinstance(api_key, str) and not (api_key.startswith('${') and api_key.endswith('}')):
                    # Replace with environment variable reference
                    provider = sanitized['llm'].get('provider', 'openai')
                    if provider == 'openai':
                        sanitized['llm']['api_key'] = '${OPENAI_API_KEY}'
                    elif provider == 'anthropic':
                        sanitized['llm']['api_key'] = '${ANTHROPIC_API_KEY}'
                    elif provider == 'azure':
                        sanitized['llm']['api_key'] = '${AZURE_OPENAI_API_KEY}'
                    else:
                        sanitized['llm']['api_key'] = None  # Remove if unknown provider
        
        # Remove API keys from connection configs
        if 'source' in sanitized and isinstance(sanitized['source'], dict):
            connection = sanitized['source']
            # Common connection fields that might contain secrets
            sensitive_fields = ['password', 'api_key', 'apiKey', 'secret', 'token', 'access_key', 'secret_key']
            for field in sensitive_fields:
                if field in connection:
                    # Only remove if it's an actual value, not an env var reference
                    value = connection[field]
                    if isinstance(value, str) and not (value.startswith('${') and value.endswith('}')):
                        connection[field] = None  # Remove from file
        
        return sanitized
    
    def _ensure_history_table(self) -> bool:
        """
        Ensure the config history table exists, create it if it doesn't.
        
        Returns:
            True if table exists or was created, False otherwise
        """
        if not self.db_engine:
            return False
        
        try:
            # Check if table exists
            with self.db_engine.connect() as conn:
                # Check database type
                dialect = self.db_engine.dialect.name
                if dialect == 'postgresql':
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'baselinr_config_history'
                        )
                    """))
                elif dialect == 'sqlite':
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT name FROM sqlite_master 
                            WHERE type='table' AND name='baselinr_config_history'
                        )
                    """))
                else:
                    # For other databases, try PostgreSQL syntax
                    result = conn.execute(text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = 'baselinr_config_history'
                        )
                    """))
                
                table_exists = result.scalar()
                
                if not table_exists:
                    logger.info("Creating baselinr_config_history table...")
                    # Create the table
                    if dialect == 'postgresql':
                        conn.execute(text("""
                            CREATE TABLE baselinr_config_history (
                                version_id VARCHAR(255) PRIMARY KEY,
                                config_json JSONB NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                created_by VARCHAR(255),
                                comment TEXT
                            )
                        """))
                        conn.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_config_history_created_at 
                            ON baselinr_config_history(created_at DESC)
                        """))
                    elif dialect == 'sqlite':
                        conn.execute(text("""
                            CREATE TABLE baselinr_config_history (
                                version_id TEXT PRIMARY KEY,
                                config_json TEXT NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                created_by TEXT,
                                comment TEXT
                            )
                        """))
                        conn.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_config_history_created_at 
                            ON baselinr_config_history(created_at DESC)
                        """))
                    else:
                        # Generic SQL
                        conn.execute(text("""
                            CREATE TABLE baselinr_config_history (
                                version_id VARCHAR(255) PRIMARY KEY,
                                config_json TEXT NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                created_by VARCHAR(255),
                                comment TEXT
                            )
                        """))
                        conn.execute(text("""
                            CREATE INDEX IF NOT EXISTS idx_config_history_created_at 
                            ON baselinr_config_history(created_at DESC)
                        """))
                    conn.commit()
                    logger.info("Successfully created baselinr_config_history table")
                    return True
                else:
                    return True
        except Exception as e:
            logger.error(f"Failed to ensure history table exists: {e}", exc_info=True)
            return False
    
    def _save_to_history(self, config: Dict[str, Any], comment: Optional[str] = None, created_by: Optional[str] = None) -> str:
        """
        Save configuration to history table.
        
        Args:
            config: Configuration dictionary
            comment: Optional comment
            created_by: Optional user identifier
            
        Returns:
            Version ID (UUID)
        """
        if not self.db_engine:
            logger.warning("No database engine available, skipping history save")
            import uuid
            return str(uuid.uuid4())
        
        # Ensure table exists
        if not self._ensure_history_table():
            logger.error("Failed to ensure history table exists, skipping history save")
            import uuid
            return str(uuid.uuid4())
        
        try:
            import uuid
            version_id = str(uuid.uuid4())
            config_json = json.dumps(config)
            
            # Determine JSON column type based on database
            dialect = self.db_engine.dialect.name
            if dialect == 'postgresql':
                # PostgreSQL uses JSONB
                with self.db_engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO baselinr_config_history (version_id, config_json, created_by, comment)
                        VALUES (:version_id, CAST(:config_json AS JSONB), :created_by, :comment)
                    """), {
                        "version_id": version_id,
                        "config_json": config_json,
                        "created_by": created_by,
                        "comment": comment
                    })
            else:
                # Other databases use TEXT
                with self.db_engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO baselinr_config_history (version_id, config_json, created_by, comment)
                        VALUES (:version_id, :config_json, :created_by, :comment)
                    """), {
                        "version_id": version_id,
                        "config_json": config_json,
                        "created_by": created_by,
                        "comment": comment
                    })
            
            logger.info(f"Saved config to history with version_id: {version_id}")
            return version_id
        except Exception as e:
            logger.error(f"Failed to save config to history: {e}", exc_info=True)
            # Return a version ID anyway so save doesn't fail
            import uuid
            return str(uuid.uuid4())
    
    def restore_config_version(self, version_id: str, comment: Optional[str] = None) -> Dict[str, Any]:
        """
        Restore a configuration version as the current config.
        
        Args:
            version_id: Version ID to restore
            comment: Optional comment for the restore action
            
        Returns:
            Restored configuration dictionary
        """
        # Get the version config
        version_data = self.get_config_version(version_id)
        if not version_data:
            raise ValueError(f"Version not found: {version_id}")
        
        config_to_restore = version_data["config"]
        
        # Validate the config
        is_valid, errors = self.validate_config(config_to_restore)
        if not is_valid:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")
        
        # Save the config to file
        saved_config = self.save_config(config_to_restore)
        
        # Save to history with restore comment
        restore_comment = comment or f"Restored from version {version_id}"
        self._save_to_history(saved_config, comment=restore_comment)
        
        return saved_config



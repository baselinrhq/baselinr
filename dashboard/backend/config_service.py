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
    
    def save_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save configuration to file or database.
        
        Args:
            config: Configuration dictionary to save
            
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
                
                # Write to file based on extension
                path = Path(self._config_path)
                with open(path, 'w') as f:
                    if path.suffix in ['.yaml', '.yml']:
                        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
                    elif path.suffix == '.json':
                        json.dump(config_dict, f, indent=2)
                    else:
                        # Default to YAML
                        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
                
                logger.info(f"Config saved to: {self._config_path}")
                return config_dict
            except Exception as e:
                logger.error(f"Failed to save config: {e}")
                raise RuntimeError(f"Failed to save configuration: {e}")
        else:
            # If no config path, just return validated config
            logger.warning("No config file path configured, config not persisted")
            return validated_config.model_dump(exclude_none=True)
    
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



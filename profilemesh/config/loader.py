"""
Configuration loader for ProfileMesh.

Loads and validates configuration from YAML/JSON files with
support for environment variable overrides.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .schema import ProfileMeshConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and validates ProfileMesh configuration files."""
    
    @staticmethod
    def load_from_file(filepath: str) -> ProfileMeshConfig:
        """
        Load configuration from a YAML or JSON file.
        
        Args:
            filepath: Path to configuration file
            
        Returns:
            Validated ProfileMeshConfig instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        
        # Load based on file extension
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                config_dict = yaml.safe_load(f)
            elif path.suffix == '.json':
                config_dict = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")
        
        # Apply environment variable overrides
        config_dict = ConfigLoader._apply_env_overrides(config_dict)
        
        # Validate and return
        try:
            return ProfileMeshConfig(**config_dict)
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}")
    
    @staticmethod
    def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Environment variables should be prefixed with PROFILEMESH_
        and use double underscores for nesting:
        PROFILEMESH_SOURCE__HOST=localhost
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment overrides applied
        """
        env_prefix = "PROFILEMESH_"
        
        for key, value in os.environ.items():
            if not key.startswith(env_prefix):
                continue
            
            # Parse nested path
            path = key[len(env_prefix):].lower().split("__")
            
            # Navigate to the nested location
            current = config
            for part in path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the value
            current[path[-1]] = ConfigLoader._parse_env_value(value)
            logger.debug(f"Applied env override: {key} = {value}")
        
        return config
    
    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """
        Parse environment variable value to appropriate Python type.
        
        Args:
            value: String value from environment variable
            
        Returns:
            Parsed value (str, int, float, bool, or original string)
        """
        # Try boolean
        if value.lower() in ['true', 'yes', '1']:
            return True
        if value.lower() in ['false', 'no', '0']:
            return False
        
        # Try numeric
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    @staticmethod
    def load_from_dict(config_dict: Dict[str, Any]) -> ProfileMeshConfig:
        """
        Load configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Validated ProfileMeshConfig instance
        """
        return ProfileMeshConfig(**config_dict)


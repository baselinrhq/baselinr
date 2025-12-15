"""
Configuration loader for Baselinr.

Loads and validates configuration from YAML/JSON files with
support for environment variable overrides.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml  # type: ignore[import-untyped]

from .dataset_loader import DatasetFileLoader
from .schema import BaselinrConfig, DatasetsConfig, DatasetsDirectoryConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and validates Baselinr configuration files."""

    @staticmethod
    def load_from_file(filepath: str) -> BaselinrConfig:
        """
        Load configuration from a YAML or JSON file.

        Args:
            filepath: Path to configuration file

        Returns:
            Validated BaselinrConfig instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        # Load based on file extension
        with open(path, "r") as f:
            if path.suffix in [".yaml", ".yml"]:
                config_dict = yaml.safe_load(f)
            elif path.suffix == ".json":
                config_dict = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")

        # Apply environment variable overrides
        config_dict = ConfigLoader._apply_env_overrides(config_dict)

        # Expand environment variables in config values (e.g., ${OPENAI_API_KEY})
        config_dict = ConfigLoader._expand_env_vars(config_dict)

        # Validate and create config
        try:
            config = BaselinrConfig(**config_dict)
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}")

        # If datasets is a directory config, load from directory
        if isinstance(config.datasets, DatasetsDirectoryConfig):
            loader = DatasetFileLoader(config_file_path=path)
            dataset_configs = loader.load_from_directory(config.datasets)

            # Replace directory config with loaded datasets
            config.datasets = DatasetsConfig(datasets=dataset_configs)

        return config

    @staticmethod
    def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.

        Environment variables should be prefixed with BASELINR_
        and use double underscores for nesting:
        BASELINR_SOURCE__HOST=localhost

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with environment overrides applied
        """
        env_prefix = "BASELINR_"

        for key, value in os.environ.items():
            if not key.startswith(env_prefix):
                continue

            # Parse nested path
            path = key[len(env_prefix) :].lower().split("__")

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
        if value.lower() in ["true", "yes", "1"]:
            return True
        if value.lower() in ["false", "no", "0"]:
            return False

        # Try numeric
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Return as string
        return value

    @staticmethod
    def _expand_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand environment variable references in config values.

        Supports syntax like ${VAR_NAME} or ${VAR_NAME:default_value}.

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with environment variables expanded
        """
        import re

        def expand_value(value: Any) -> Any:
            """Recursively expand environment variables in config values."""
            if isinstance(value, str):
                # Match ${VAR_NAME} or ${VAR_NAME:default}
                pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"
                matches = re.findall(pattern, value)

                if matches:
                    result = value
                    for var_name, default_val in matches:
                        env_value = os.environ.get(var_name)
                        if env_value is not None:
                            replacement = env_value
                        elif default_val:
                            replacement = default_val
                        else:
                            # Keep original if no env var and no default
                            continue
                        result = result.replace(f"${{{var_name}}}", replacement)
                        result = result.replace(f"${{{var_name}:{default_val}}}", replacement)
                    return result
                return value
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            else:
                return value

        return expand_value(config)  # type: ignore[no-any-return]

    @staticmethod
    def load_from_dict(config_dict: Dict[str, Any]) -> BaselinrConfig:
        """
        Load configuration from a dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Validated BaselinrConfig instance
        """
        # Expand environment variables
        config_dict = ConfigLoader._expand_env_vars(config_dict)
        return BaselinrConfig(**config_dict)

"""
Configuration loader for Baselinr.

Loads and validates configuration from YAML/JSON files with
support for environment variable overrides and ODCS contracts.
"""

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import yaml  # type: ignore[import-untyped]

from .schema import BaselinrConfig, ContractsConfig

if TYPE_CHECKING:
    from baselinr.contracts import ODCSContract

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and validates Baselinr configuration files and ODCS contracts."""

    # Cache for loaded contracts
    _contracts_cache: Dict[str, List["ODCSContract"]] = {}

    @staticmethod
    def load_from_file(
        filepath: str,
        load_contracts: bool = True,
    ) -> BaselinrConfig:
        """
        Load configuration from a YAML or JSON file.

        Args:
            filepath: Path to configuration file
            load_contracts: Whether to also load ODCS contracts (default: True)

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
        with open(path, "r", encoding="utf-8") as f:
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

        # Load ODCS contracts if configured
        if load_contracts and config.contracts:
            contracts = ConfigLoader.load_contracts(
                config.contracts,
                base_path=path.parent,
            )
            # Store in cache for later retrieval
            ConfigLoader._contracts_cache[str(path.absolute())] = contracts
            logger.info(f"Loaded {len(contracts)} ODCS contract(s)")

        return config

    @staticmethod
    def load_contracts(
        contracts_config: ContractsConfig,
        base_path: Optional[Path] = None,
    ) -> List["ODCSContract"]:
        """
        Load ODCS contracts from the configured directory.

        Args:
            contracts_config: Contracts configuration
            base_path: Base path for relative directory resolution

        Returns:
            List of loaded ODCSContract objects
        """
        from baselinr.contracts import ContractLoader, ContractLoadError

        # Resolve contracts directory
        contracts_dir = Path(contracts_config.directory)
        if not contracts_dir.is_absolute() and base_path:
            contracts_dir = base_path / contracts_dir

        if not contracts_dir.exists():
            logger.warning(f"Contracts directory not found: {contracts_dir}")
            return []

        # Create loader with configuration
        loader = ContractLoader(
            validate_on_load=contracts_config.validate_on_load,
            file_patterns=contracts_config.file_patterns,
        )

        try:
            contracts = loader.load_from_directory(
                str(contracts_dir),
                recursive=contracts_config.recursive,
                exclude_patterns=contracts_config.exclude_patterns,
            )
            return contracts
        except ContractLoadError as e:
            logger.error(f"Failed to load contracts: {e}")
            return []

    @staticmethod
    def get_cached_contracts(config_path: str) -> List["ODCSContract"]:
        """
        Get cached contracts for a configuration file.

        Args:
            config_path: Path to the configuration file

        Returns:
            List of cached ODCSContract objects, or empty list if not cached
        """
        path = Path(config_path).absolute()
        return ConfigLoader._contracts_cache.get(str(path), [])

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

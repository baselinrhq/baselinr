"""
ODCS Contract Loader.

Loads and parses ODCS data contracts from YAML files.
"""

import logging
import os
from pathlib import Path
from typing import Any, List, Optional

import yaml  # type: ignore[import-untyped]

from .odcs_schema import ODCSContract
from .validator import ODCSValidationError, ODCSValidator

logger = logging.getLogger(__name__)


class ContractLoadError(Exception):
    """Error loading a contract file."""

    def __init__(self, filepath: str, message: str, cause: Optional[Exception] = None):
        self.filepath = filepath
        self.message = message
        self.cause = cause
        super().__init__(f"Error loading contract '{filepath}': {message}")


class ContractLoader:
    """
    Loads ODCS data contracts from files and directories.

    Example:
        >>> loader = ContractLoader()
        >>> contracts = loader.load_from_directory("./contracts")
        >>> contract = loader.load_from_file("./contracts/customers.odcs.yaml")
    """

    def __init__(
        self,
        validate_on_load: bool = True,
        file_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize the contract loader.

        Args:
            validate_on_load: Whether to validate contracts when loading
            file_patterns: File patterns to match (default: ["*.odcs.yaml", "*.odcs.yml"])
        """
        self.validate_on_load = validate_on_load
        self.file_patterns = file_patterns or ["*.odcs.yaml", "*.odcs.yml"]
        self.validator = ODCSValidator()

    def load_from_file(self, filepath: str) -> ODCSContract:
        """
        Load a single ODCS contract from a file.

        Args:
            filepath: Path to the contract file

        Returns:
            Parsed ODCSContract

        Raises:
            ContractLoadError: If file cannot be loaded or parsed
            ODCSValidationError: If validation fails
        """
        path = Path(filepath)

        if not path.exists():
            raise ContractLoadError(filepath, "File not found")

        if not path.is_file():
            raise ContractLoadError(filepath, "Path is not a file")

        # Load YAML content
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ContractLoadError(filepath, f"Invalid YAML: {e}", e)
        except IOError as e:
            raise ContractLoadError(filepath, f"Cannot read file: {e}", e)

        if not content:
            raise ContractLoadError(filepath, "Empty file or invalid content")

        if not isinstance(content, dict):
            raise ContractLoadError(filepath, f"Expected dict, got {type(content).__name__}")

        # Expand environment variables
        content = self._expand_env_vars(content)

        # Parse into model
        try:
            contract = ODCSContract(**content)
        except Exception as e:
            raise ContractLoadError(filepath, f"Invalid contract structure: {e}", e)

        # Validate if enabled
        if self.validate_on_load:
            errors = self.validator.validate(contract)
            if errors:
                raise ODCSValidationError(
                    f"Contract validation failed for '{filepath}'",
                    errors=errors,
                )

        logger.debug(f"Loaded contract from {filepath}: {contract.id or 'unnamed'}")
        return contract

    def load_from_directory(
        self,
        directory: str,
        recursive: bool = True,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[ODCSContract]:
        """
        Load all ODCS contracts from a directory.

        Args:
            directory: Path to the contracts directory
            recursive: Whether to search subdirectories
            exclude_patterns: Glob patterns to exclude

        Returns:
            List of parsed ODCSContract objects

        Raises:
            ContractLoadError: If directory doesn't exist
        """
        path = Path(directory)

        if not path.exists():
            raise ContractLoadError(directory, "Directory not found")

        if not path.is_dir():
            raise ContractLoadError(directory, "Path is not a directory")

        exclude_patterns = exclude_patterns or []
        contracts: List[ODCSContract] = []
        errors: List[str] = []

        # Find all matching files
        files = self._find_contract_files(path, recursive, exclude_patterns)

        logger.info(f"Found {len(files)} contract file(s) in {directory}")

        # Load each file
        for filepath in files:
            try:
                contract = self.load_from_file(str(filepath))
                contracts.append(contract)
            except (ContractLoadError, ODCSValidationError) as e:
                errors.append(str(e))
                logger.warning(f"Failed to load contract: {e}")

        if errors:
            logger.warning(f"Loaded {len(contracts)} contracts with {len(errors)} error(s)")
        else:
            logger.info(f"Successfully loaded {len(contracts)} contract(s)")

        return contracts

    def _find_contract_files(
        self,
        directory: Path,
        recursive: bool,
        exclude_patterns: List[str],
    ) -> List[Path]:
        """Find all contract files matching patterns."""
        files: List[Path] = []

        for pattern in self.file_patterns:
            if recursive:
                matched = list(directory.rglob(pattern))
            else:
                matched = list(directory.glob(pattern))

            # Filter out excluded patterns
            for filepath in matched:
                excluded = False
                for exclude in exclude_patterns:
                    if filepath.match(exclude):
                        excluded = True
                        break

                if not excluded and filepath not in files:
                    files.append(filepath)

        # Sort for consistent ordering
        files.sort()
        return files

    def _expand_env_vars(self, obj: Any) -> Any:
        """
        Expand environment variable references in config values.

        Supports syntax like ${VAR_NAME} or ${VAR_NAME:default_value}.
        """
        import re

        if isinstance(obj, str):
            pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"
            matches = re.findall(pattern, obj)

            if matches:
                result = obj
                for var_name, default_val in matches:
                    env_value = os.environ.get(var_name)
                    if env_value is not None:
                        replacement = env_value
                    elif default_val:
                        replacement = default_val
                    else:
                        continue
                    result = result.replace(f"${{{var_name}}}", replacement)
                    result = result.replace(f"${{{var_name}:{default_val}}}", replacement)
                return result
            return obj
        elif isinstance(obj, dict):
            return {k: self._expand_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._expand_env_vars(item) for item in obj]
        else:
            return obj


def load_contract(filepath: str, validate: bool = True) -> ODCSContract:
    """
    Convenience function to load a single contract.

    Args:
        filepath: Path to the contract file
        validate: Whether to validate the contract

    Returns:
        Parsed ODCSContract
    """
    loader = ContractLoader(validate_on_load=validate)
    return loader.load_from_file(filepath)


def load_contracts(
    directory: str,
    recursive: bool = True,
    validate: bool = True,
) -> List[ODCSContract]:
    """
    Convenience function to load contracts from a directory.

    Args:
        directory: Path to the contracts directory
        recursive: Whether to search subdirectories
        validate: Whether to validate contracts

    Returns:
        List of parsed ODCSContract objects
    """
    loader = ContractLoader(validate_on_load=validate)
    return loader.load_from_directory(directory, recursive=recursive)

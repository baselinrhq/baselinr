"""
Validation provider registry for Baselinr.

Manages multiple validation providers and coordinates validation execution.
"""

import logging
from typing import List, Optional

from sqlalchemy.engine import Engine

from .base import ValidationProvider, ValidationResult, ValidationRule

logger = logging.getLogger(__name__)


class ValidationProviderRegistry:
    """Registry for managing validation providers."""

    def __init__(self, config=None, source_engine: Optional[Engine] = None):
        """
        Initialize registry.

        Args:
            config: Optional BaselinrConfig to pass to providers
            source_engine: Optional SQLAlchemy engine for source database
        """
        self.config = config
        self.source_engine = source_engine
        self._providers: List[ValidationProvider] = []
        self._auto_register()

    def _auto_register(self):
        """Auto-register built-in provider."""
        # Register built-in provider (always available)
        try:
            from .builtin_provider import BuiltinValidationProvider

            if self.source_engine:
                builtin_provider = BuiltinValidationProvider(self.source_engine)
                self.register_provider(builtin_provider)
        except Exception as e:
            logger.debug(f"Could not register built-in provider: {e}")

        # Future: Register other providers (Great Expectations, Soda, etc.)
        # based on config and availability

    def register_provider(self, provider: ValidationProvider):
        """
        Register a validation provider.

        Args:
            provider: ValidationProvider instance
        """
        if provider not in self._providers:
            self._providers.append(provider)
            logger.debug(f"Registered validation provider: {provider.get_provider_name()}")

    def get_available_providers(self) -> List[ValidationProvider]:
        """
        Get list of available providers.

        Returns:
            List of providers where is_available() returns True
        """
        return [p for p in self._providers if p.is_available()]

    def get_provider(self, name: str) -> Optional[ValidationProvider]:
        """
        Get a specific provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None if not found
        """
        for provider in self._providers:
            if provider.get_provider_name() == name:
                return provider
        return None

    def validate_rules(
        self,
        rules: List[ValidationRule],
        provider_name: Optional[str] = None,
    ) -> List[ValidationResult]:
        """
        Execute validation rules using the specified or default provider.

        Args:
            rules: List of ValidationRule objects to execute
            provider_name: Optional provider name to use. If None, uses built-in provider.

        Returns:
            List of ValidationResult objects
        """
        if provider_name:
            provider = self.get_provider(provider_name)
            if not provider:
                logger.warning(f"Provider '{provider_name}' not found, using built-in provider")
                provider = self.get_provider("builtin")
        else:
            # Default to built-in provider
            provider = self.get_provider("builtin")

        if not provider:
            logger.error("No validation provider available")
            return [
                ValidationResult(
                    rule=rule,
                    passed=False,
                    failure_reason="No validation provider available",
                    total_rows=0,
                    failed_rows=0,
                    failure_rate=0.0,
                )
                for rule in rules
            ]

        if not provider.is_available():
            logger.error(f"Provider '{provider.get_provider_name()}' is not available")
            return [
                ValidationResult(
                    rule=rule,
                    passed=False,
                    failure_reason=f"Provider '{provider.get_provider_name()}' is not available",
                    total_rows=0,
                    failed_rows=0,
                    failure_rate=0.0,
                )
                for rule in rules
            ]

        try:
            return provider.validate_rules(rules)
        except Exception as e:
            logger.error(f"Error executing validation rules: {e}", exc_info=True)
            return [
                ValidationResult(
                    rule=rule,
                    passed=False,
                    failure_reason=f"Validation error: {str(e)}",
                    total_rows=0,
                    failed_rows=0,
                    failure_rate=0.0,
                )
                for rule in rules
            ]

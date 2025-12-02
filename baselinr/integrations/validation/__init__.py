"""
Validation integration for Baselinr.

Provides a provider-based architecture for data validation from
multiple sources (built-in validators, Great Expectations, Soda, etc.).
"""

from .base import ValidationProvider, ValidationResult, ValidationRule

# Optional providers - import only if available
try:
    from .builtin_provider import BuiltinValidationProvider
except (ImportError, ModuleNotFoundError):
    BuiltinValidationProvider = None  # type: ignore

__all__ = [
    "ValidationProvider",
    "ValidationResult",
    "ValidationRule",
    "BuiltinValidationProvider",
]

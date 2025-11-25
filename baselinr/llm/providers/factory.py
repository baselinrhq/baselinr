"""
Factory for creating LLM provider instances.

Maps provider names to provider classes and handles initialization.
"""

from typing import TYPE_CHECKING

from ..base import LLMConfigError, LLMProvider

if TYPE_CHECKING:
    from ..base import LLMConfig  # noqa: F401


def create_provider(config: "LLMConfig") -> LLMProvider:  # type: ignore[name-defined]
    """
    Create LLM provider instance based on configuration.

    Args:
        config: LLM configuration

    Returns:
        Initialized LLM provider instance

    Raises:
        LLMConfigError: If provider is unknown or initialization fails
    """
    provider_name = config.provider.lower()

    if provider_name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(config)

    elif provider_name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(config)

    elif provider_name == "azure":
        from .azure import AzureOpenAIProvider

        return AzureOpenAIProvider(config)

    elif provider_name == "ollama":
        from .ollama import OllamaProvider

        return OllamaProvider(config)

    else:
        raise LLMConfigError(f"Unknown LLM provider: {provider_name}")

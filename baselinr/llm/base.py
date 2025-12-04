"""
Base classes and interfaces for LLM providers.

Defines the abstract base class that all LLM providers must implement,
along with response models and custom exceptions.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..config.schema import LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from an LLM provider."""

    text: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[float] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    """List of tool calls in format: [{"id": str, "function": {"name": str, "arguments": dict}}]"""


class LLMAPIError(Exception):
    """Raised when an LLM API call fails."""

    pass


class LLMConfigError(Exception):
    """Raised when LLM configuration is invalid."""

    pass


class LLMTimeoutError(Exception):
    """Raised when an LLM API call times out."""

    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: "LLMConfig"):
        """
        Initialize LLM provider.

        Args:
            config: LLM configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """
        Generate completion from LLM.

        Args:
            prompt: User prompt text
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            LLMAPIError: If API call fails
            LLMTimeoutError: If request times out
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate provider configuration (API key, etc.).

        Returns:
            True if configuration is valid

        Raises:
            LLMConfigError: If configuration is invalid
        """
        pass

    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate completion with tool calling support.

        This method supports multi-turn conversations and function calling.
        If not overridden by a provider, it falls back to simple generation.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: Optional list of tool definitions in provider format
            temperature: Sampling temperature (uses config default if not specified)
            max_tokens: Maximum tokens to generate (uses config default if not specified)

        Returns:
            LLMResponse with generated text, tool calls, and metadata

        Raises:
            LLMAPIError: If API call fails
            LLMTimeoutError: If request times out
            NotImplementedError: If provider doesn't support tool calling
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support tool calling. "
            "Use generate() for simple text generation."
        )

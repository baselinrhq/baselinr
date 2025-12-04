"""
Anthropic provider implementation for LLM explanations.

Supports Claude models via Anthropic API.
"""

import logging
import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..base import LLMConfig

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..base import LLMAPIError, LLMConfigError, LLMProvider, LLMResponse, LLMTimeoutError

logger = logging.getLogger(__name__)

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None  # type: ignore[assignment,misc]


class AnthropicProvider(LLMProvider):
    """Anthropic provider for LLM explanations."""

    def __init__(self, config: "LLMConfig"):
        """
        Initialize Anthropic provider.

        Args:
            config: LLM configuration
        """
        super().__init__(config)

        if not ANTHROPIC_AVAILABLE:
            raise LLMConfigError(
                "Anthropic library not installed. Install with: pip install anthropic>=0.18.0"
            )

        # Get API key from config or environment
        api_key = self._get_api_key()
        if not api_key:
            raise LLMConfigError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or configure llm.api_key in config."
            )

        self.client = anthropic.Anthropic(api_key=api_key, timeout=self.config.timeout)
        self.model = self.config.model or "claude-sonnet-4-20250514"

    def _get_api_key(self) -> Optional[str]:
        """Get API key from config or environment."""
        if self.config.api_key:
            return self.config.api_key
        return os.environ.get("ANTHROPIC_API_KEY")

    def validate_config(self) -> bool:
        """
        Validate Anthropic configuration.

        Returns:
            True if configuration is valid

        Raises:
            LLMConfigError: If configuration is invalid
        """
        if not ANTHROPIC_AVAILABLE:
            raise LLMConfigError("Anthropic library not installed")

        api_key = self._get_api_key()
        if not api_key:
            raise LLMConfigError("Anthropic API key not found")

        if not self.model:
            raise LLMConfigError("Model name is required")

        return True

    @retry(
        retry=retry_if_exception_type((anthropic.APIError, anthropic.APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """
        Generate completion from Anthropic API.

        Args:
            prompt: User prompt text
            system_prompt: Optional system prompt
            temperature: Sampling temperature (uses config default if not specified)
            max_tokens: Maximum tokens to generate (uses config default if not specified)

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            LLMAPIError: If API call fails
            LLMTimeoutError: If request times out
        """
        start_time = time.time()

        # Use config defaults if not specified
        temp = temperature if temperature is not None else self.config.temperature
        max_toks = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            # Anthropic API structure
            messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
            system_message = system_prompt if system_prompt else None

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_toks,
                temperature=temp,
                system=system_message,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
                timeout=self.config.timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract response
            if response.content and len(response.content) > 0:
                first_block = response.content[0]
                if hasattr(first_block, "text"):
                    content = first_block.text
                else:
                    content = ""
            else:
                content = ""
            tokens_used = (
                response.usage.input_tokens + response.usage.output_tokens
                if response.usage
                else None
            )

            # Estimate cost (rough estimates for Claude models)
            cost_usd = self._estimate_cost(tokens_used, self.model) if tokens_used else None

            return LLMResponse(
                text=content,
                model=self.model,
                provider="anthropic",
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
            )

        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(f"Anthropic API request timed out: {e}") from e
        except (anthropic.APIError, anthropic.APIConnectionError) as e:
            raise LLMAPIError(f"Anthropic API error: {e}") from e
        except Exception as e:
            raise LLMAPIError(f"Unexpected error calling Anthropic API: {e}") from e

    def _estimate_cost(self, tokens: int, model: str) -> Optional[float]:
        """
        Estimate cost in USD for API call.

        Args:
            tokens: Number of tokens used
            model: Model name

        Returns:
            Estimated cost in USD or None if unknown model
        """
        # Rough cost estimates per 1M tokens (as of 2024)
        # These are approximate and may change
        cost_per_million = {
            "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
            "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
            "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
            "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        }

        if model not in cost_per_million:
            return None

        # Rough estimate: assume 70% input, 30% output tokens
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)

        costs = cost_per_million[model]
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]

        return input_cost + output_cost

    @retry(
        retry=retry_if_exception_type((anthropic.APIError, anthropic.APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate completion with tool calling support.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            tools: Optional list of tool definitions in Anthropic format
            temperature: Sampling temperature (uses config default if not specified)
            max_tokens: Maximum tokens to generate (uses config default if not specified)

        Returns:
            LLMResponse with generated text, tool calls, and metadata

        Raises:
            LLMAPIError: If API call fails
            LLMTimeoutError: If request times out
        """
        start_time = time.time()

        # Use config defaults if not specified
        temp = temperature if temperature is not None else self.config.temperature
        max_toks = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            # Extract system message (Anthropic uses separate system parameter)
            system_content = None
            filtered_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                else:
                    filtered_messages.append(msg)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_toks,
                temperature=temp,
                system=system_content,  # type: ignore[arg-type]
                messages=filtered_messages,  # type: ignore[arg-type]
                tools=tools if tools else None,  # type: ignore[arg-type]
                timeout=self.config.timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract response
            content = ""
            tool_calls = []

            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text
                elif hasattr(block, "type") and block.type == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.id,
                            "function": {
                                "name": block.name,
                                "arguments": block.input,
                            },
                        }
                    )

            tokens_used = None
            if response.usage:
                tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Estimate cost
            cost_usd = self._estimate_cost(tokens_used, self.model) if tokens_used else None

            return LLMResponse(
                text=content,
                model=self.model,
                provider="anthropic",
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                tool_calls=tool_calls if tool_calls else None,
            )

        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(f"Anthropic API request timed out: {e}") from e
        except (anthropic.APIError, anthropic.APIConnectionError) as e:
            raise LLMAPIError(f"Anthropic API error: {e}") from e
        except Exception as e:
            raise LLMAPIError(f"Unexpected error calling Anthropic API: {e}") from e

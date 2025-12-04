"""
Azure OpenAI provider implementation for LLM explanations.

Supports GPT models via Azure OpenAI API.
"""

import json
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
    from openai import AzureOpenAI
    from openai._exceptions import APIError, APITimeoutError

    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    AzureOpenAI = None  # type: ignore[assignment,misc]
    APIError = Exception  # type: ignore[assignment,misc]
    APITimeoutError = Exception  # type: ignore[assignment,misc]


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider for LLM explanations."""

    def __init__(self, config: "LLMConfig"):
        """
        Initialize Azure OpenAI provider.

        Args:
            config: LLM configuration
        """
        super().__init__(config)

        if not AZURE_AVAILABLE:
            raise LLMConfigError(
                "OpenAI library not installed. Install with: pip install openai>=1.0.0"
            )

        # Get Azure-specific configuration
        api_key = self._get_api_key()
        endpoint = self._get_endpoint()
        api_version = self._get_api_version()

        if not api_key:
            raise LLMConfigError(
                "Azure OpenAI API key not found. Set AZURE_OPENAI_API_KEY environment variable "
                "or configure llm.api_key in config."
            )

        if not endpoint:
            raise LLMConfigError(
                "Azure OpenAI endpoint not found. Set AZURE_OPENAI_ENDPOINT environment variable "
                "or configure llm.extra_params.endpoint in config."
            )

        self.client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            timeout=self.config.timeout,
        )
        self.model = self.config.model

    def _get_api_key(self) -> Optional[str]:
        """Get API key from config or environment."""
        if self.config.api_key:
            return self.config.api_key
        return os.environ.get("AZURE_OPENAI_API_KEY")

    def _get_endpoint(self) -> Optional[str]:
        """Get endpoint from config or environment."""
        # Check config rate_limit dict (used for Azure-specific params)
        if self.config.rate_limit and isinstance(self.config.rate_limit, dict):
            endpoint = self.config.rate_limit.get("endpoint")
            if endpoint:
                return str(endpoint)

        # Check environment variable
        result: Optional[str] = os.environ.get("AZURE_OPENAI_ENDPOINT")
        return result

    def _get_api_version(self) -> str:
        """Get API version from config or environment."""
        # Check config rate_limit dict (used for Azure-specific params)
        if self.config.rate_limit and isinstance(self.config.rate_limit, dict):
            api_version = self.config.rate_limit.get("api_version")
            if api_version:
                return str(api_version)

        # Check environment variable
        default_version = "2024-02-15-preview"
        return str(os.environ.get("AZURE_OPENAI_API_VERSION", default_version))

    def validate_config(self) -> bool:
        """
        Validate Azure OpenAI configuration.

        Returns:
            True if configuration is valid

        Raises:
            LLMConfigError: If configuration is invalid
        """
        if not AZURE_AVAILABLE:
            raise LLMConfigError("OpenAI library not installed")

        api_key = self._get_api_key()
        if not api_key:
            raise LLMConfigError("Azure OpenAI API key not found")

        endpoint = self._get_endpoint()
        if not endpoint:
            raise LLMConfigError("Azure OpenAI endpoint not found")

        if not self.config.model:
            raise LLMConfigError("Model name is required")

        return True

    @retry(
        retry=retry_if_exception_type((APIError,)),
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
        Generate completion from Azure OpenAI API.

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
            messages: list[dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temp,
                max_tokens=max_toks,
                timeout=self.config.timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Extract response
            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else None

            # Estimate cost (same as OpenAI)
            cost_usd = self._estimate_cost(tokens_used, self.model) if tokens_used else None

            return LLMResponse(
                text=content,
                model=self.model,
                provider="azure",
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
            )

        except APITimeoutError as e:
            raise LLMTimeoutError(f"Azure OpenAI API request timed out: {e}") from e
        except APIError as e:
            raise LLMAPIError(f"Azure OpenAI API error: {e}") from e
        except Exception as e:
            raise LLMAPIError(f"Unexpected error calling Azure OpenAI API: {e}") from e

    def _estimate_cost(self, tokens: int, model: str) -> Optional[float]:
        """
        Estimate cost in USD for API call.

        Args:
            tokens: Number of tokens used
            model: Model name

        Returns:
            Estimated cost in USD or None if unknown model
        """
        # Rough cost estimates per 1M tokens (same as OpenAI)
        cost_per_million = {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
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
        retry=retry_if_exception_type((APIError,)),
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
            tools: Optional list of tool definitions in OpenAI format
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
            # Build kwargs for API call
            api_kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,  # type: ignore[arg-type]
                "temperature": temp,
                "max_tokens": max_toks,
                "timeout": self.config.timeout,  # type: ignore[arg-type]
            }

            # Only add tools and tool_choice if tools are provided
            if tools:
                api_kwargs["tools"] = tools  # type: ignore[arg-type]
                api_kwargs["tool_choice"] = "auto"  # type: ignore[arg-type]

            response = self.client.chat.completions.create(**api_kwargs)

            latency_ms = (time.time() - start_time) * 1000

            # Extract response
            message = response.choices[0].message
            content = message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else None

            # Extract tool calls
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": json.loads(tc.function.arguments),
                            },
                        }
                    )

            # Estimate cost
            cost_usd = self._estimate_cost(tokens_used, self.model) if tokens_used else None

            return LLMResponse(
                text=content,
                model=self.model,
                provider="azure",
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                tool_calls=tool_calls if tool_calls else None,
            )

        except APITimeoutError as e:
            raise LLMTimeoutError(f"Azure OpenAI API request timed out: {e}") from e
        except APIError as e:
            raise LLMAPIError(f"Azure OpenAI API error: {e}") from e
        except Exception as e:
            raise LLMAPIError(f"Unexpected error calling Azure OpenAI API: {e}") from e

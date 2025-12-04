"""
Ollama provider implementation for LLM explanations.

Supports local models via Ollama API (for air-gapped deployments).
"""

import logging
import os
import time
from typing import TYPE_CHECKING, Optional

import httpx

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


class OllamaProvider(LLMProvider):
    """Ollama provider for LLM explanations (local models)."""

    def __init__(self, config: "LLMConfig"):
        """
        Initialize Ollama provider.

        Args:
            config: LLM configuration
        """
        super().__init__(config)

        # Get base URL from config or environment
        self.base_url = self._get_base_url()
        self.model = self.config.model or "llama2"

        # Create HTTP client
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.config.timeout,
        )

    def _get_base_url(self) -> str:
        """Get Ollama base URL from config or environment."""
        # Check config rate_limit dict (used for extra params)
        if self.config.rate_limit and isinstance(self.config.rate_limit, dict):
            base_url = self.config.rate_limit.get("base_url")
            if base_url:
                return str(base_url)

        # Check environment variable
        result: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return result

    def validate_config(self) -> bool:
        """
        Validate Ollama configuration.

        Returns:
            True if configuration is valid

        Raises:
            LLMConfigError: If configuration is invalid
        """
        if not self.model:
            raise LLMConfigError("Model name is required")

        # Try to connect to Ollama to verify it's running
        try:
            response = self.client.get("/api/tags", timeout=5)
            if response.status_code != 200:
                raise LLMConfigError(f"Ollama API returned status {response.status_code}")
        except httpx.ConnectError:
            raise LLMConfigError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running and accessible."
            )
        except Exception as e:
            raise LLMConfigError(f"Failed to validate Ollama connection: {e}")

        return True

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.RequestError)),
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
        Generate completion from Ollama API.

        Args:
            prompt: User prompt text
            system_prompt: Optional system prompt (combined with prompt for Ollama)
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
            # Combine system prompt and user prompt for Ollama
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Ollama API request
            request_data = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temp,
                    "num_predict": max_toks,
                },
            }

            response = self.client.post(
                "/api/generate",
                json=request_data,
                timeout=self.config.timeout,
            )

            if response.status_code != 200:
                raise LLMAPIError(
                    f"Ollama API returned status {response.status_code}: {response.text}"
                )

            result = response.json()

            latency_ms = (time.time() - start_time) * 1000

            # Extract response
            content = result.get("response", "")
            # Ollama doesn't provide token usage in standard format
            tokens_used = None

            return LLMResponse(
                text=content,
                model=self.model,
                provider="ollama",
                tokens_used=tokens_used,
                cost_usd=None,  # Local models have no cost
                latency_ms=latency_ms,
            )

        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"Ollama API request timed out: {e}") from e
        except httpx.HTTPError as e:
            raise LLMAPIError(f"Ollama API error: {e}") from e
        except Exception as e:
            raise LLMAPIError(f"Unexpected error calling Ollama API: {e}") from e

    def generate_with_tools(
        self,
        messages: list,
        tools: Optional[list] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate completion with tool calling support.

        Note: Ollama does not support standardized tool calling.
        This method raises NotImplementedError.

        Raises:
            NotImplementedError: Ollama does not support tool calling
        """
        raise NotImplementedError(
            "Ollama provider does not support tool calling. "
            "Use generate() for simple text generation, or use OpenAI/Anthropic "
            "providers for tool calling."
        )

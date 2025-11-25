# LLM Provider Guide

This guide explains how to add new LLM providers to Baselinr.

## Provider Interface

All providers must implement the `LLMProvider` abstract base class:

```python
from baselinr.llm.base import LLMProvider, LLMResponse, LLMConfigError

class MyProvider(LLMProvider):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        # Initialize your provider client
        
    def validate_config(self) -> bool:
        """Validate configuration and return True if valid."""
        # Check API keys, endpoints, etc.
        return True
        
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> LLMResponse:
        """Generate completion and return LLMResponse."""
        # Call your provider's API
        # Return LLMResponse with text, model, provider, etc.
        pass
```

## Required Methods

### `validate_config() -> bool`

Validates that the provider can be initialized with the given configuration. Should raise `LLMConfigError` if configuration is invalid.

### `generate(...) -> LLMResponse`

Generates a completion from the LLM. Should:
- Handle timeouts and raise `LLMTimeoutError`
- Handle API errors and raise `LLMAPIError`
- Return `LLMResponse` with:
  - `text`: Generated explanation
  - `model`: Model name used
  - `provider`: Provider name
  - `tokens_used`: Optional token count
  - `cost_usd`: Optional cost estimate
  - `latency_ms`: Optional latency in milliseconds

## Example: Adding a New Provider

1. **Create provider file:**
   ```python
   # baselinr/baselinr/llm/providers/myprovider.py
   from ..base import LLMProvider, LLMResponse, LLMConfigError
   
   class MyProvider(LLMProvider):
       def __init__(self, config):
           super().__init__(config)
           # Initialize client
           
       def validate_config(self) -> bool:
           # Validate config
           return True
           
       def generate(self, prompt, system_prompt=None, temperature=0.3, max_tokens=500):
           # Generate response
           return LLMResponse(
               text="...",
               model=self.config.model,
               provider="myprovider",
           )
   ```

2. **Register in factory:**
   ```python
   # baselinr/baselinr/llm/providers/factory.py
   def create_provider(config: LLMConfig) -> LLMProvider:
       if config.provider == "myprovider":
           from .myprovider import MyProvider
           return MyProvider(config)
       # ... other providers
   ```

3. **Update schema:**
   ```python
   # baselinr/baselinr/config/schema.py
   # Add "myprovider" to valid providers list in LLMConfig
   ```

## Testing Your Provider

Create tests in `tests/llm/test_providers_myprovider.py`:

```python
def test_myprovider_initialization():
    """Test provider initialization."""
    config = LLMConfig(
        enabled=True,
        provider="myprovider",
        api_key="test-key",
        model="test-model",
    )
    provider = MyProvider(config)
    assert provider.validate_config()

def test_myprovider_generate():
    """Test generation with mocks."""
    # Mock API calls
    # Test error handling
    # Test response formatting
```

## Best Practices

1. **Use retry logic** - Use `tenacity` for transient failures
2. **Handle timeouts** - Respect `config.timeout`
3. **Log appropriately** - Use `self.logger` for warnings/errors
4. **Estimate costs** - Provide cost estimates if possible
5. **Track tokens** - Return token usage if available
6. **Graceful degradation** - Raise appropriate exceptions for fallback

## Provider Requirements

- Must support system prompts (or combine with user prompt)
- Must support temperature parameter
- Must support max_tokens parameter
- Should handle rate limiting gracefully
- Should provide meaningful error messages

## Existing Providers

Reference implementations:
- **OpenAI:** `baselinr/baselinr/llm/providers/openai.py`
- **Anthropic:** `baselinr/baselinr/llm/providers/anthropic.py`
- **Azure:** `baselinr/baselinr/llm/providers/azure.py`
- **Ollama:** `baselinr/baselinr/llm/providers/ollama.py`


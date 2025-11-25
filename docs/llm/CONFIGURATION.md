# LLM Configuration Guide

This guide explains how to configure LLM-powered human-readable explanations for Baselinr alerts.

## Overview

Baselinr supports multiple LLM providers to generate natural language explanations for data drift, anomalies, and schema changes. This feature is opt-in and disabled by default.

## Quick Start

1. Set your API key as an environment variable:
   ```bash
   export OPENAI_API_KEY=sk-...
   ```

2. Enable LLM in your `config.yml`:
   ```yaml
   llm:
     enabled: true
     provider: openai
     api_key: ${OPENAI_API_KEY}
     model: gpt-4o-mini
   ```

3. Run drift detection - explanations will be automatically generated!

## Configuration Options

### Basic Configuration

```yaml
llm:
  enabled: true                    # Enable LLM explanations (default: false)
  provider: openai                 # Provider: openai | anthropic | azure | ollama
  api_key: ${OPENAI_API_KEY}      # API key (supports env var expansion)
  model: gpt-4o-mini              # Model name (provider-specific)
  temperature: 0.3                # Sampling temperature (0.0-2.0)
  max_tokens: 500                 # Maximum tokens per explanation
  timeout: 30                     # API timeout in seconds
  fallback_to_template: true      # Use templates if LLM fails
```

### Provider-Specific Configuration

#### OpenAI

```yaml
llm:
  enabled: true
  provider: openai
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o-mini  # Options: gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-3.5-turbo
```

**Environment Variable:** `OPENAI_API_KEY`

#### Anthropic

```yaml
llm:
  enabled: true
  provider: anthropic
  api_key: ${ANTHROPIC_API_KEY}
  model: claude-sonnet-4-20250514
```

**Environment Variable:** `ANTHROPIC_API_KEY`

#### Azure OpenAI

```yaml
llm:
  enabled: true
  provider: azure
  api_key: ${AZURE_OPENAI_API_KEY}
  model: gpt-4o-mini
  rate_limit:
    endpoint: https://your-resource.openai.azure.com
    api_version: 2024-02-15-preview
```

**Environment Variables:**
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION` (optional, defaults to `2024-02-15-preview`)

#### Ollama (Local)

```yaml
llm:
  enabled: true
  provider: ollama
  model: llama2  # Or mistral, codellama, etc.
  rate_limit:
    base_url: http://localhost:11434  # Optional, defaults to localhost:11434
```

**Environment Variable:** `OLLAMA_BASE_URL` (optional, defaults to `http://localhost:11434`)

**Note:** Ollama must be running locally. Install from https://ollama.ai

## Environment Variable Expansion

The `api_key` field supports environment variable expansion using `${VAR_NAME}` syntax:

```yaml
llm:
  api_key: ${OPENAI_API_KEY}  # Expands to value of OPENAI_API_KEY env var
```

You can also provide defaults:

```yaml
llm:
  api_key: ${OPENAI_API_KEY:sk-default-key}  # Uses default if env var not set
```

## Troubleshooting

### LLM Not Generating Explanations

1. **Check if LLM is enabled:**
   ```yaml
   llm:
     enabled: true  # Must be explicitly set
   ```

2. **Verify API key:**
   ```bash
   echo $OPENAI_API_KEY  # Should output your key
   ```

3. **Check logs for errors:**
   - LLM failures are logged as warnings
   - System falls back to templates automatically

### Common Errors

**"OpenAI API key not found"**
- Set `OPENAI_API_KEY` environment variable
- Or configure `llm.api_key` in config

**"Anthropic library not installed"**
- Install: `pip install anthropic>=0.18.0`

**"Ollama connection failed"**
- Ensure Ollama is running: `ollama serve`
- Check `OLLAMA_BASE_URL` if using custom endpoint

### Fallback Behavior

If LLM fails for any reason, Baselinr automatically falls back to template-based explanations. This ensures you always get explanations, even if:
- API key is invalid
- Network is unavailable
- API rate limits are hit
- Provider service is down

To disable fallback (and get no explanations on LLM failure):
```yaml
llm:
  fallback_to_template: false
```

## Cost Considerations

LLM explanations incur API costs. Estimated costs per explanation:

- **GPT-4o-mini:** ~$0.0001 per explanation
- **GPT-4o:** ~$0.001 per explanation
- **Claude Sonnet:** ~$0.0005 per explanation
- **Ollama:** Free (local)

For 1000 explanations/month:
- GPT-4o-mini: ~$0.10
- GPT-4o: ~$1.00
- Claude Sonnet: ~$0.50

## Best Practices

1. **Start with GPT-4o-mini** - Best cost/quality ratio
2. **Use templates for high-volume alerts** - Disable LLM for non-critical tables
3. **Monitor API usage** - Check provider dashboards for usage
4. **Set appropriate timeouts** - 30s default is usually sufficient
5. **Use Ollama for air-gapped deployments** - No external API calls

## Examples

See `examples/config.yml` for complete configuration examples.


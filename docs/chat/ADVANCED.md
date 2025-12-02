# Baselinr Chat - Advanced Usage

This guide covers advanced usage patterns and customization options for the Baselinr Chat interface.

## Configuration Options

### Full LLM Configuration

```yaml
llm:
  enabled: true
  provider: openai          # openai | anthropic | azure | ollama
  model: gpt-4o-mini        # Model name specific to provider
  temperature: 0.3          # Lower = more focused, higher = more creative
  max_tokens: 1500          # Maximum tokens per response
  timeout: 30               # API timeout in seconds
  fallback_to_template: true  # Use templates if LLM fails
  
  # Chat-specific settings
  chat:
    enabled: true
    max_history_messages: 20    # Messages to keep in context
    max_iterations: 5           # Max tool-calling iterations per query
    tool_timeout: 30            # Tool execution timeout
    cache_tool_results: true    # Cache results within session
    enable_context_enhancement: true  # Add extra context to responses
```

### Provider-Specific Configuration

#### OpenAI

```yaml
llm:
  enabled: true
  provider: openai
  model: gpt-4o-mini  # or gpt-4o, gpt-3.5-turbo
  # api_key: ${OPENAI_API_KEY}  # Uses env var by default
```

#### Anthropic

```yaml
llm:
  enabled: true
  provider: anthropic
  model: claude-sonnet-4-20250514  # or claude-3-haiku-20240307
  # api_key: ${ANTHROPIC_API_KEY}
```

#### Azure OpenAI

```yaml
llm:
  enabled: true
  provider: azure
  model: your-deployment-name
  # Additional Azure config via environment variables:
  # AZURE_OPENAI_API_KEY
  # AZURE_OPENAI_ENDPOINT
```

#### Ollama (Local)

```yaml
llm:
  enabled: true
  provider: ollama
  model: llama2  # or mistral, codellama, etc.
  # No API key needed for local Ollama
```

## Context Window Management

The chat agent automatically manages the context window to stay within token limits.

### How It Works

1. **System prompt** - Always included, contains agent instructions and tool descriptions
2. **Recent messages** - Last N messages from conversation (configurable)
3. **Tool results** - Automatically truncated if too large
4. **Pruning** - Older messages removed when approaching limit

### Customizing Context

```bash
# Keep more history for complex investigations
baselinr chat --config config.yml --max-history 50

# Reduce history for faster responses
baselinr chat --config config.yml --max-history 10
```

## Tool Calling Patterns

### Multi-Tool Queries

For complex questions, the agent may call multiple tools:

```
🧑 You: Are there any patterns in recent anomalies?

# Agent internally calls:
# 1. query_anomalies() - Get recent anomalies
# 2. query_drift_events() - Get related drift
# 3. search_tables() - Find affected tables
# 4. get_lineage() - Check for correlated upstream issues
```

### Iteration Limits

Set max iterations to control how many tool calls per query:

```bash
# Allow more iterations for thorough investigation
baselinr chat --config config.yml --max-iterations 10

# Limit iterations for faster (but potentially less complete) answers
baselinr chat --config config.yml --max-iterations 3
```

## Session Management

### Session State

Each chat session maintains:
- Conversation history
- Tool result cache
- Context variables
- Usage statistics

### Clearing State

```
# Clear conversation history (keeps session)
/clear

# View current session stats
/stats

# View conversation history
/history
```

## Cost Optimization

### Token Usage

Monitor token usage with `/stats`:

```
🧑 You: /stats

Session Statistics:
| Metric | Value |
|--------|-------|
| Tokens Used | 4,523 |
| Est. Cost | $0.0007 |
```

### Reducing Costs

1. **Use efficient models** - `gpt-4o-mini` is 60x cheaper than `gpt-4-turbo`
2. **Reduce history** - Fewer messages = fewer input tokens
3. **Be specific** - Targeted questions need fewer tool calls
4. **Clear history** - Use `/clear` between unrelated investigations

### Cost Estimates by Model

| Provider | Model | Input $/1M | Output $/1M |
|----------|-------|------------|-------------|
| OpenAI | gpt-4o-mini | $0.15 | $0.60 |
| OpenAI | gpt-4o | $2.50 | $10.00 |
| Anthropic | claude-3-haiku | $0.25 | $1.25 |
| Anthropic | claude-sonnet-4 | $3.00 | $15.00 |

## Error Handling

### Graceful Degradation

When the LLM fails:
1. Agent retries with exponential backoff
2. Falls back to template-based responses if configured
3. Displays helpful error message

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| API key not found | Missing environment variable | Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` |
| Rate limit exceeded | Too many requests | Wait and retry, or upgrade plan |
| Context length exceeded | Too much history | Use `/clear` or reduce `--max-history` |
| Tool timeout | Slow database query | Increase `--tool-timeout` |

## Debugging

### Verbose Mode

Enable verbose mode to see tool calls:

```bash
baselinr chat --config config.yml --verbose

# Or toggle during session
/verbose
```

### Debug Logging

Enable debug logging:

```bash
baselinr --debug chat --config config.yml
```

This shows:
- LLM API calls and responses
- Tool execution details
- Context window usage
- Timing information

## Programmatic Usage

### Python API

```python
from baselinr.chat.agent import create_agent, AgentConfig
from baselinr.chat.session import ChatSession
from sqlalchemy import create_engine

# Setup
engine = create_engine("postgresql://...")
config = AgentConfig(max_iterations=5)

# Create agent
agent = create_agent(
    llm_config={"provider": "openai", "model": "gpt-4o-mini", "enabled": True},
    storage_engine=engine,
    storage_config={"runs_table": "baselinr_runs", "results_table": "baselinr_results"},
    agent_config=config,
)

# Create session and chat
session = ChatSession.create(config={})
response = agent.process_message("What tables have been profiled?", session)
print(response)
```

### Custom Tools

Add custom tools for your specific use cases:

```python
from baselinr.chat.tools import Tool, ToolRegistry

def my_custom_query(table: str, days: int = 7):
    """Custom query for business-specific metrics."""
    # Your implementation here
    return {"result": "..."}

# Register the tool
registry = ToolRegistry()
registry.register(Tool(
    name="my_custom_query",
    description="Query business-specific metrics",
    parameters={
        "type": "object",
        "properties": {
            "table": {"type": "string", "description": "Table name"},
            "days": {"type": "integer", "description": "Lookback days"},
        },
        "required": ["table"],
    },
    function=my_custom_query,
    category="custom",
))
```

## Future Features (Cloud Edition)

These features are planned for the Baselinr Cloud edition:

- **Web UI Chat** - Chat interface in the dashboard
- **Team Chat** - Shared conversations with @mentions
- **Persistent History** - Chat history saved across sessions
- **Scheduled Investigations** - Automated chat-based monitoring
- **Slack/Teams Integration** - Chat from your collaboration tools
- **Voice Input** - Voice-to-text queries

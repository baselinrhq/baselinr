# Baselinr Chat - Getting Started

The Baselinr Chat interface allows you to interactively query and investigate your data quality monitoring using natural language.

## Prerequisites

1. **LLM Provider Configuration**: You need an LLM provider configured (OpenAI, Anthropic, Azure, or Ollama)
2. **Profiling Data**: Run some profiling first to have data to query
3. **Python packages**: `rich` and optionally `prompt_toolkit` for enhanced CLI experience

## Quick Start

### 1. Configure LLM in your config.yml

```yaml
# config.yml
source:
  type: postgres
  host: localhost
  database: mydb
  username: user
  password: password

storage:
  connection:
    type: postgres
    host: localhost
    database: baselinr_meta
    username: user
    password: password

# Add LLM configuration for chat
llm:
  enabled: true
  provider: openai      # or anthropic, azure, ollama
  model: gpt-4o-mini    # provider-specific model name
  # api_key: ${OPENAI_API_KEY}  # Optional, uses env var by default
```

### 2. Set your API key

For OpenAI:
```bash
export OPENAI_API_KEY=your-api-key
```

For Anthropic:
```bash
export ANTHROPIC_API_KEY=your-api-key
```

### 3. Start the chat

```bash
baselinr chat --config config.yml
```

### 4. Ask questions!

```
🧑 You: what tables have been profiled recently?

🤖 Baselinr:
I found 5 tables profiled in the last 7 days:

1. **orders** - Last profiled 2 hours ago
   - 2.3M rows, 15 columns
   - No active alerts

2. **customers** - Last profiled 3 hours ago
   - 450K rows, 22 columns
   - 1 HIGH severity drift alert on email column

[...]
```

## Available Commands

Within the chat session, you can use these commands:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/history` | Show conversation history |
| `/stats` | Show session statistics (tokens used, cost estimate) |
| `/tools` | List available query tools |
| `/verbose` | Toggle verbose mode |
| `/exit` | Exit the chat |

## CLI Options

```bash
baselinr chat --config config.yml [OPTIONS]

Options:
  --max-iterations N    Maximum tool-calling iterations (default: 5)
  --max-history N       Maximum messages in context (default: 20)
  --tool-timeout N      Tool execution timeout in seconds (default: 30)
  --show-tools          Show tool calls in output
  --verbose, -v         Enable verbose output
```

## Next Steps

- See [EXAMPLES.md](EXAMPLES.md) for example conversations
- See [TOOLS.md](TOOLS.md) for available query tools
- See [ADVANCED.md](ADVANCED.md) for advanced usage patterns

"""
CLI chat command implementation for Baselinr.

Provides the `baselinr chat` command for interactive data quality conversations.
"""

import logging

from baselinr.chat.agent import AgentConfig, ChatAgent, create_agent
from baselinr.chat.renderer import ChatRenderer
from baselinr.chat.session import ChatSession

logger = logging.getLogger(__name__)

# Check for prompt_toolkit availability
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.history import InMemoryHistory

    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False
    PromptSession = None
    InMemoryHistory = None
    AutoSuggestFromHistory = None


def run_chat_command(args) -> int:
    """
    Run the chat command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code
    """
    from baselinr.config.loader import ConfigLoader
    from baselinr.connectors.factory import create_connector

    # Load configuration
    try:
        config = ConfigLoader.load_from_file(args.config)
    except Exception as e:
        print(f"Error loading config: {e}")
        return 1

    # Check if LLM is configured
    if not config.llm or not config.llm.enabled:
        print("Error: LLM is not configured or not enabled.")
        print("Please configure the 'llm' section in your config file:")
        print(
            """
llm:
  enabled: true
  provider: openai  # or anthropic, azure, ollama
  model: gpt-4o-mini
  # api_key: ${OPENAI_API_KEY}  # Optional, uses env var by default
"""
        )
        return 1

    # Create storage connection
    try:
        connector = create_connector(config.storage.connection, config.retry)
        engine = connector.engine
    except Exception as e:
        print(f"Error connecting to storage: {e}")
        return 1

    # Build storage config dict
    storage_config = {
        "runs_table": config.storage.runs_table,
        "results_table": config.storage.results_table,
        "events_table": "baselinr_events",
    }

    # Create agent config
    agent_config = AgentConfig(
        max_iterations=getattr(args, "max_iterations", 5),
        max_history_messages=getattr(args, "max_history", 20),
        tool_timeout=getattr(args, "tool_timeout", 30),
        temperature=0.3,
        max_tokens=1500,
    )

    # Create renderer
    renderer = ChatRenderer(
        show_tool_calls=getattr(args, "show_tools", False),
        verbose=getattr(args, "verbose", False),
    )

    try:
        # Create agent
        agent = create_agent(
            llm_config=config.llm.model_dump(),
            storage_engine=engine,
            storage_config=storage_config,
            agent_config=agent_config,
        )
    except Exception as e:
        print(f"Error creating chat agent: {e}")
        logger.exception("Failed to create chat agent")
        return 1

    # Create session
    session = ChatSession.create(config=storage_config)

    # Run chat loop
    return _run_chat_loop(agent, session, renderer, args)


def _run_chat_loop(
    agent: ChatAgent,
    session: ChatSession,
    renderer: ChatRenderer,
    args,
) -> int:
    """
    Run the interactive chat loop.

    Args:
        agent: Chat agent
        session: Chat session
        renderer: Chat renderer
        args: Command line arguments

    Returns:
        Exit code
    """
    # Display welcome message
    renderer.render_welcome()

    # Setup prompt
    if PROMPT_TOOLKIT_AVAILABLE:
        prompt_session = PromptSession(
            history=InMemoryHistory(),
            auto_suggest=AutoSuggestFromHistory(),
        )
    else:
        prompt_session = None

    while True:
        try:
            # Get user input
            if prompt_session:
                user_input = prompt_session.prompt("\n🧑 You: ")
            else:
                user_input = input("\n🧑 You: ")

            # Handle empty input
            if not user_input.strip():
                continue

            # Handle commands
            if user_input.startswith("/"):
                should_continue = _handle_command(
                    user_input.strip(),
                    session,
                    renderer,
                    agent,
                )
                if not should_continue:
                    break
                continue

            # Show thinking indicator
            thinking_status = renderer.render_thinking()
            if thinking_status:
                thinking_status.__enter__()

            try:
                # Process message
                response = agent.process_message(user_input, session)

                if thinking_status:
                    thinking_status.__exit__(None, None, None)

                # Display response
                renderer.render_assistant_message(response)

            except KeyboardInterrupt:
                if thinking_status:
                    thinking_status.__exit__(None, None, None)
                renderer.render_info("Interrupted")
                continue

            except Exception as e:
                if thinking_status:
                    thinking_status.__exit__(None, None, None)
                logger.exception("Error processing message")
                renderer.render_error(str(e))

        except (EOFError, KeyboardInterrupt):
            renderer.render_goodbye()
            break

        except Exception as e:
            logger.exception("Unexpected error in chat loop")
            renderer.render_error(f"Unexpected error: {e}")

    # Show final stats
    stats = session.get_stats()
    if stats.get("total_messages", 0) > 0:
        renderer.render_stats(stats)

    return 0


def _handle_command(
    command: str,
    session: ChatSession,
    renderer: ChatRenderer,
    agent: ChatAgent,
) -> bool:
    """
    Handle chat commands.

    Args:
        command: Command string (starting with /)
        session: Chat session
        renderer: Chat renderer
        agent: Chat agent

    Returns:
        True to continue chat loop, False to exit
    """
    cmd = command.lower().split()[0]

    if cmd == "/help":
        renderer.render_help()

    elif cmd == "/clear":
        session.clear_history()
        agent.clear_cache()
        renderer.render_success("Conversation history cleared")

    elif cmd == "/history":
        renderer.render_history(session.get_history())

    elif cmd == "/stats":
        renderer.render_stats(session.get_stats())

    elif cmd == "/tools":
        renderer.render_tools(agent.tools.list_tools())

    elif cmd == "/verbose":
        renderer.verbose = not renderer.verbose
        status = "enabled" if renderer.verbose else "disabled"
        renderer.render_info(f"Verbose mode {status}")

    elif cmd == "/exit" or cmd == "/quit":
        renderer.render_goodbye()
        return False

    else:
        renderer.render_warning(f"Unknown command: {command}")
        renderer.render_info("Type /help for available commands")

    return True


def add_chat_parser(subparsers) -> None:
    """
    Add chat parser to CLI subparsers.

    Args:
        subparsers: argparse subparsers object
    """
    chat_parser = subparsers.add_parser(
        "chat",
        help="Start interactive chat session for data quality investigation",
    )
    chat_parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to configuration file (YAML or JSON)",
    )
    chat_parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum tool-calling iterations (default: 5)",
    )
    chat_parser.add_argument(
        "--max-history",
        type=int,
        default=20,
        help="Maximum messages to keep in context (default: 20)",
    )
    chat_parser.add_argument(
        "--tool-timeout",
        type=int,
        default=30,
        help="Tool execution timeout in seconds (default: 30)",
    )
    chat_parser.add_argument(
        "--show-tools",
        action="store_true",
        help="Show tool calls in output",
    )
    chat_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

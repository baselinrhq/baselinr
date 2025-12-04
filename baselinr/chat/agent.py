"""
Chat agent for Baselinr conversational interface.

Implements the tool-using LLM pattern for natural language data quality queries.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from baselinr.chat.context import ContextEnhancer, get_conversation_context
from baselinr.chat.history import build_messages_for_llm
from baselinr.chat.session import ChatSession
from baselinr.chat.tools import ToolRegistry

logger = logging.getLogger(__name__)

# System prompt for the chat agent
SYSTEM_PROMPT = """You are Baselinr Assistant, an AI data quality expert helping users \
understand and investigate their data monitoring results.

You have access to tools that let you query profiling runs, drift events, anomalies, \
and historical trends from the Baselinr monitoring system.

When answering questions:
1. Use the appropriate tools to retrieve relevant data
2. Synthesize information from multiple sources if needed
3. Provide clear, actionable insights
4. Suggest follow-up investigations when appropriate
5. Be concise but thorough
6. Format responses in markdown for readability
7. Use emoji sparingly for severity indicators (🔴 high, 🟡 medium, 🟢 low)

Available tools:
{tool_descriptions}

Key concepts:
- **Profiling runs**: Regular scans of tables to collect metrics \
(row count, null rates, distributions, etc.)
- **Drift**: Significant changes in data distribution or metrics compared to baseline
- **Anomalies**: Statistically unusual values that may indicate data quality issues
- **Lineage**: Upstream sources and downstream dependents of a table

When investigating issues:
- Start by understanding the scope (what tables, columns, metrics are affected)
- Check recent activity and historical trends
- Look for correlated events (multiple issues around the same time)
- Suggest root cause hypotheses when appropriate

Always think step-by-step about what data you need to answer the user's question."""


@dataclass
class AgentConfig:
    """Configuration for the chat agent."""

    max_iterations: int = 5  # Maximum tool-calling iterations
    max_history_messages: int = 20  # Messages to include in context
    tool_timeout: int = 30  # Tool execution timeout in seconds
    temperature: float = 0.3
    max_tokens: int = 1500
    enable_context_enhancement: bool = True
    cache_tool_results: bool = True


@dataclass
class ToolCallResult:
    """Result from executing a tool call."""

    tool_name: str
    tool_call_id: str
    output: str
    success: bool
    execution_time_ms: float
    error: Optional[str] = None


class ChatAgent:
    """LLM agent that can use tools to answer questions about data quality."""

    def __init__(
        self,
        llm_provider,
        tool_registry: ToolRegistry,
        config: AgentConfig,
        context_enhancer: Optional[ContextEnhancer] = None,
    ):
        """
        Initialize the chat agent.

        Args:
            llm_provider: LLM provider instance (OpenAI, Anthropic, etc.)
            tool_registry: Registry of available tools
            config: Agent configuration
            context_enhancer: Optional context enhancer for rich responses
        """
        self.llm = llm_provider
        self.tools = tool_registry
        self.config = config
        self.context_enhancer = context_enhancer
        self._tool_cache: Dict[str, Any] = {}
        self._provider_type = self._detect_provider_type()

    def _detect_provider_type(self) -> str:
        """Detect the LLM provider type."""
        provider_class = self.llm.__class__.__name__.lower()
        if "anthropic" in provider_class:
            return "anthropic"
        elif "openai" in provider_class or "azure" in provider_class:
            return "openai"
        elif "ollama" in provider_class:
            return "ollama"
        return "openai"  # Default to OpenAI format

    def _build_system_prompt(self) -> str:
        """Build system prompt with tool descriptions."""
        tool_descriptions = self.tools.get_tool_descriptions()
        return SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)

    def process_message(self, user_message: str, session: ChatSession) -> str:
        """
        Process a user message and generate response (sync wrapper).

        Args:
            user_message: The user's message
            session: The chat session

        Returns:
            The assistant's response
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.process_message_async(user_message, session))

    async def process_message_async(self, user_message: str, session: ChatSession) -> str:
        """
        Process a user message and generate response.

        This implements the tool-using pattern:
        1. Send message + tools to LLM
        2. LLM decides which tools to call
        3. Execute tool calls
        4. Send results back to LLM
        5. LLM generates final response

        Args:
            user_message: The user's message
            session: The chat session

        Returns:
            The assistant's response
        """
        # Add user message to session
        session.add_message("user", user_message)

        # Build conversation context
        conversation_context = get_conversation_context(session)
        system_prompt = self._build_system_prompt()
        if conversation_context:
            system_prompt += f"\n\nRecent context: {conversation_context}"

        iteration = 0
        total_tokens = 0
        all_tool_calls = []

        while iteration < self.config.max_iterations:
            iteration += 1
            logger.debug(f"Agent iteration {iteration}")

            # Prepare messages for LLM
            messages = build_messages_for_llm(
                session.messages,
                system_prompt,
                provider=self._provider_type,
                max_history=self.config.max_history_messages,
            )

            try:
                # Call LLM with tools
                response = await self._call_llm_with_tools(messages)

                if response.get("tokens_used"):
                    total_tokens += response["tokens_used"]

                # Check if LLM wants to call tools
                tool_calls = response.get("tool_calls", [])

                if tool_calls:
                    # Execute tool calls
                    tool_results = await self._execute_tools(tool_calls)
                    all_tool_calls.extend(tool_results)

                    # Add assistant message with tool calls
                    session.add_message(
                        "assistant",
                        response.get("content", ""),
                        tool_calls=tool_calls,
                        tokens_used=response.get("tokens_used"),
                    )

                    # Add tool results as messages
                    for result in tool_results:
                        session.add_message(
                            "tool",
                            result.output,
                            tool_results=[{"id": result.tool_call_id, "output": result.output}],
                        )

                    # Continue loop - LLM will process tool results
                    continue
                else:
                    # LLM generated final response
                    final_response: str = str(response.get("content", ""))

                    # Add final response to session
                    session.add_message(
                        "assistant",
                        final_response,
                        tokens_used=total_tokens,
                        metadata={
                            "iterations": iteration,
                            "tool_calls": len(all_tool_calls),
                        },
                    )

                    return final_response

            except Exception as e:
                logger.error(f"Error in agent iteration {iteration}: {e}")
                if iteration >= self.config.max_iterations:
                    raise

                # Try to continue with error context
                session.add_message(
                    "tool",
                    f"Error: {str(e)}",
                    tool_results=[{"id": "error", "output": str(e)}],
                )

        # Max iterations reached
        fallback_response = (
            "I apologize, but I'm having trouble processing your request. "
            "Please try rephrasing your question or breaking it into smaller parts."
        )

        session.add_message(
            "assistant",
            fallback_response,
            metadata={"error": "max_iterations_reached"},
        )

        return fallback_response

    async def _call_llm_with_tools(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Call the LLM with tools enabled using the LLMProvider interface.

        Args:
            messages: Formatted messages for the LLM

        Returns:
            Dict with 'content', 'tool_calls', and 'tokens_used'
        """
        # Get tools in appropriate format
        if self._provider_type == "anthropic":
            tools = self.tools.to_anthropic_format()
        else:
            tools = self.tools.to_openai_format()

        # Call LLM using the provider's generate_with_tools method
        # Wrap in executor since it's a synchronous call
        loop = asyncio.get_event_loop()

        def _call():
            return self.llm.generate_with_tools(
                messages=messages,
                tools=tools if tools else None,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

        try:
            response = await loop.run_in_executor(None, _call)

            # Convert LLMResponse to dict format expected by chat agent
            return {
                "content": response.text,
                "tool_calls": response.tool_calls or [],
                "tokens_used": response.tokens_used,
            }
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise

    async def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[ToolCallResult]:
        """
        Execute tool calls and return results.

        Args:
            tool_calls: List of tool calls from LLM

        Returns:
            List of ToolCallResult objects
        """
        results = []

        for call in tool_calls:
            tool_name = call["function"]["name"]
            tool_args = call["function"]["arguments"]
            tool_call_id = call.get("id", f"call_{tool_name}")

            start_time = time.time()

            # Check cache
            cache_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
            if self.config.cache_tool_results and cache_key in self._tool_cache:
                cached = self._tool_cache[cache_key]
                results.append(
                    ToolCallResult(
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        output=cached,
                        success=True,
                        execution_time_ms=0,
                    )
                )
                continue

            tool = self.tools.get_tool(tool_name)
            if not tool:
                results.append(
                    ToolCallResult(
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        output=json.dumps({"error": f"Tool '{tool_name}' not found"}),
                        success=False,
                        execution_time_ms=0,
                        error=f"Tool '{tool_name}' not found",
                    )
                )
                continue

            try:
                # Execute tool function
                if asyncio.iscoroutinefunction(tool.function):
                    output = await asyncio.wait_for(
                        tool.function(**tool_args),
                        timeout=self.config.tool_timeout,
                    )
                else:
                    loop = asyncio.get_event_loop()
                    output = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: tool.function(**tool_args)),
                        timeout=self.config.tool_timeout,
                    )

                execution_time = (time.time() - start_time) * 1000

                # Serialize output
                if isinstance(output, (dict, list)):
                    output_str = json.dumps(output, default=str)
                else:
                    output_str = str(output)

                # Enhance with context if available
                if (
                    self.context_enhancer
                    and self.config.enable_context_enhancement
                    and isinstance(output, dict)
                ):
                    if tool_name == "query_drift_events" and "drift" in str(output).lower():
                        output = self.context_enhancer.enhance_drift_event(output)
                        output_str = json.dumps(output, default=str)

                # Cache result
                if self.config.cache_tool_results:
                    self._tool_cache[cache_key] = output_str

                results.append(
                    ToolCallResult(
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        output=output_str,
                        success=True,
                        execution_time_ms=execution_time,
                    )
                )

            except asyncio.TimeoutError:
                results.append(
                    ToolCallResult(
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        output=json.dumps({"error": f"Tool '{tool_name}' timed out"}),
                        success=False,
                        execution_time_ms=self.config.tool_timeout * 1000,
                        error="Timeout",
                    )
                )

            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                results.append(
                    ToolCallResult(
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        output=json.dumps({"error": str(e)}),
                        success=False,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        error=str(e),
                    )
                )

        return results

    def clear_cache(self) -> None:
        """Clear the tool result cache."""
        self._tool_cache.clear()


def create_agent(
    llm_config: Dict[str, Any],
    storage_engine,
    storage_config: Dict[str, Any],
    agent_config: Optional[AgentConfig] = None,
) -> ChatAgent:
    """
    Create a chat agent from configuration.

    Args:
        llm_config: LLM configuration dictionary
        storage_engine: SQLAlchemy engine for storage
        storage_config: Storage configuration dictionary
        agent_config: Optional agent configuration

    Returns:
        Configured ChatAgent instance
    """
    from baselinr.chat.tools import ToolRegistry, setup_tools
    from baselinr.config.schema import LLMConfig
    from baselinr.llm.providers.factory import create_provider

    # Create LLM provider
    llm_config_obj = LLMConfig(**llm_config)
    llm_provider = create_provider(llm_config_obj)

    # Setup tools
    tool_registry = ToolRegistry()
    setup_tools(tool_registry, storage_engine, storage_config)

    # Create context enhancer
    context_enhancer = ContextEnhancer(
        engine=storage_engine,
        config=storage_config,
    )

    # Use default config if not provided
    if agent_config is None:
        agent_config = AgentConfig()

    return ChatAgent(
        llm_provider=llm_provider,
        tool_registry=tool_registry,
        config=agent_config,
        context_enhancer=context_enhancer,
    )

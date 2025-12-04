"""Tests for the chat agent."""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from baselinr.chat.agent import AgentConfig, ChatAgent, ToolCallResult
from baselinr.chat.session import ChatSession
from baselinr.chat.tools import Tool, ToolRegistry
from baselinr.llm.base import LLMResponse


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0
        self.client = MagicMock()
        self.model = "test-model"

        # Setup client mock for OpenAI-style responses
        self._setup_client_mock()

    def _setup_client_mock(self):
        """Setup the client mock to return proper responses."""
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "This is a test response."
        mock_message.tool_calls = None
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_response.usage = MagicMock(total_tokens=100)

        self.client.chat.completions.create = MagicMock(return_value=mock_response)

    def generate_with_tools(
        self, messages, tools=None, temperature=None, max_tokens=None
    ):
        """Mock generate_with_tools method."""
        self.call_count += 1
        return LLMResponse(
            text="This is a test response.",
            model=self.model,
            provider="test",
            tokens_used=100,
            tool_calls=None,
        )


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AgentConfig()

        assert config.max_iterations == 5
        assert config.max_history_messages == 20
        assert config.tool_timeout == 30
        assert config.temperature == 0.3
        assert config.cache_tool_results is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = AgentConfig(
            max_iterations=10,
            max_history_messages=50,
            tool_timeout=60,
        )

        assert config.max_iterations == 10
        assert config.max_history_messages == 50
        assert config.tool_timeout == 60


class TestToolCallResult:
    """Tests for ToolCallResult."""

    def test_successful_result(self):
        """Test creating a successful tool result."""
        result = ToolCallResult(
            tool_name="test_tool",
            tool_call_id="call_123",
            output='{"result": "success"}',
            success=True,
            execution_time_ms=50.0,
        )

        assert result.tool_name == "test_tool"
        assert result.success is True
        assert result.error is None

    def test_failed_result(self):
        """Test creating a failed tool result."""
        result = ToolCallResult(
            tool_name="test_tool",
            tool_call_id="call_123",
            output='{"error": "Failed"}',
            success=False,
            execution_time_ms=100.0,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"


class TestChatAgent:
    """Tests for the ChatAgent class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.llm = MockLLMProvider()
        self.registry = ToolRegistry()
        self.config = AgentConfig()

        # Register a test tool
        self.registry.register(
            Tool(
                name="test_query",
                description="A test query tool",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                    },
                },
                function=lambda query="": {"result": f"Query result for: {query}"},
            )
        )

    def test_create_agent(self):
        """Test creating a chat agent."""
        agent = ChatAgent(
            llm_provider=self.llm,
            tool_registry=self.registry,
            config=self.config,
        )

        assert agent.llm == self.llm
        assert agent.tools == self.registry
        assert agent.config == self.config

    def test_detect_provider_type_openai(self):
        """Test detecting OpenAI provider type."""
        mock_llm = MagicMock()
        mock_llm.__class__.__name__ = "OpenAIProvider"

        agent = ChatAgent(
            llm_provider=mock_llm,
            tool_registry=self.registry,
            config=self.config,
        )

        assert agent._provider_type == "openai"

    def test_detect_provider_type_anthropic(self):
        """Test detecting Anthropic provider type."""
        mock_llm = MagicMock()
        mock_llm.__class__.__name__ = "AnthropicProvider"

        agent = ChatAgent(
            llm_provider=mock_llm,
            tool_registry=self.registry,
            config=self.config,
        )

        assert agent._provider_type == "anthropic"

    def test_build_system_prompt(self):
        """Test building system prompt."""
        agent = ChatAgent(
            llm_provider=self.llm,
            tool_registry=self.registry,
            config=self.config,
        )

        prompt = agent._build_system_prompt()

        assert "Baselinr Assistant" in prompt
        assert "test_query" in prompt

    def test_process_message_sync(self):
        """Test synchronous message processing."""
        agent = ChatAgent(
            llm_provider=self.llm,
            tool_registry=self.registry,
            config=self.config,
        )

        session = ChatSession.create(config={})
        response = agent.process_message("Hello", session)

        assert isinstance(response, str)
        assert len(session.messages) >= 2  # User message + assistant response

    def test_clear_cache(self):
        """Test clearing the tool result cache."""
        agent = ChatAgent(
            llm_provider=self.llm,
            tool_registry=self.registry,
            config=self.config,
        )

        # Add something to cache
        agent._tool_cache["test_key"] = "test_value"
        assert len(agent._tool_cache) == 1

        agent.clear_cache()
        assert len(agent._tool_cache) == 0


class TestExecuteTools:
    """Tests for tool execution."""

    def setup_method(self):
        """Setup test fixtures."""
        self.llm = MockLLMProvider()
        self.registry = ToolRegistry()
        self.config = AgentConfig()

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Test successful tool execution."""
        # Register a simple tool
        self.registry.register(
            Tool(
                name="simple_tool",
                description="A simple tool",
                parameters={"type": "object", "properties": {}},
                function=lambda: {"status": "success"},
            )
        )

        agent = ChatAgent(
            llm_provider=self.llm,
            tool_registry=self.registry,
            config=self.config,
        )

        tool_calls = [
            {
                "id": "call_1",
                "function": {"name": "simple_tool", "arguments": {}},
            }
        ]

        results = await agent._execute_tools(tool_calls)

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].tool_name == "simple_tool"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Test executing a non-existent tool."""
        agent = ChatAgent(
            llm_provider=self.llm,
            tool_registry=self.registry,
            config=self.config,
        )

        tool_calls = [
            {
                "id": "call_1",
                "function": {"name": "nonexistent_tool", "arguments": {}},
            }
        ]

        results = await agent._execute_tools(tool_calls)

        assert len(results) == 1
        assert results[0].success is False
        assert "not found" in results[0].output

    @pytest.mark.asyncio
    async def test_execute_tool_with_error(self):
        """Test tool execution with error."""

        def failing_tool():
            raise ValueError("Tool failed!")

        self.registry.register(
            Tool(
                name="failing_tool",
                description="A failing tool",
                parameters={"type": "object", "properties": {}},
                function=failing_tool,
            )
        )

        agent = ChatAgent(
            llm_provider=self.llm,
            tool_registry=self.registry,
            config=self.config,
        )

        tool_calls = [
            {
                "id": "call_1",
                "function": {"name": "failing_tool", "arguments": {}},
            }
        ]

        results = await agent._execute_tools(tool_calls)

        assert len(results) == 1
        assert results[0].success is False
        assert "Tool failed!" in results[0].error

    @pytest.mark.asyncio
    async def test_tool_result_caching(self):
        """Test that tool results are cached."""
        call_count = 0

        def counting_tool():
            nonlocal call_count
            call_count += 1
            return {"count": call_count}

        self.registry.register(
            Tool(
                name="counting_tool",
                description="Counts calls",
                parameters={"type": "object", "properties": {}},
                function=counting_tool,
            )
        )

        agent = ChatAgent(
            llm_provider=self.llm,
            tool_registry=self.registry,
            config=AgentConfig(cache_tool_results=True),
        )

        tool_calls = [
            {
                "id": "call_1",
                "function": {"name": "counting_tool", "arguments": {}},
            }
        ]

        # Execute twice
        await agent._execute_tools(tool_calls)
        await agent._execute_tools(tool_calls)

        # Should only have been called once due to caching
        assert call_count == 1

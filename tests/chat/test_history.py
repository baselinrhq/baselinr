"""Tests for conversation history management."""

import pytest

from baselinr.chat.history import (
    ConversationHistory,
    build_messages_for_llm,
)
from baselinr.chat.session import Message


class TestConversationHistory:
    """Tests for the ConversationHistory class."""

    def test_create_history(self):
        """Test creating a conversation history."""
        history = ConversationHistory(max_messages=10)
        assert history.max_messages == 10
        assert len(history.messages) == 0

    def test_add_message(self):
        """Test adding messages to history."""
        history = ConversationHistory()

        history.add(Message(role="user", content="Hello"))
        history.add(Message(role="assistant", content="Hi"))

        assert len(history.messages) == 2

    def test_prune_on_limit(self):
        """Test that messages are pruned when limit is reached."""
        history = ConversationHistory(max_messages=5)

        for i in range(10):
            history.add(Message(role="user", content=f"Message {i}"))

        assert len(history.messages) == 5
        # Should have the last 5 messages
        assert history.messages[0].content == "Message 5"

    def test_keep_system_messages_on_prune(self):
        """Test that system messages are kept during pruning."""
        history = ConversationHistory(max_messages=3)

        history.add(Message(role="system", content="System prompt"))
        history.add(Message(role="user", content="User 1"))
        history.add(Message(role="assistant", content="Assistant 1"))
        history.add(Message(role="user", content="User 2"))
        history.add(Message(role="assistant", content="Assistant 2"))

        # Should have system message + last 2 non-system messages
        assert len(history.messages) == 3
        assert history.messages[0].role == "system"

    def test_get_messages_for_openai(self):
        """Test formatting messages for OpenAI."""
        history = ConversationHistory()

        history.add(Message(role="system", content="System prompt"))
        history.add(Message(role="user", content="Hello"))
        history.add(Message(role="assistant", content="Hi"))

        formatted = history.get_messages_for_llm(provider="openai")

        assert len(formatted) == 3
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"
        assert formatted[2]["role"] == "assistant"

    def test_get_messages_for_anthropic(self):
        """Test formatting messages for Anthropic."""
        history = ConversationHistory()

        history.add(Message(role="system", content="System prompt"))
        history.add(Message(role="user", content="Hello"))

        formatted = history.get_messages_for_llm(provider="anthropic")

        assert len(formatted) == 2
        # System message should be converted to user message for Anthropic
        assert "[System]" in formatted[0]["content"]

    def test_format_tool_call_for_openai(self):
        """Test formatting tool calls for OpenAI."""
        history = ConversationHistory()

        tool_calls = [{"id": "1", "function": {"name": "test", "arguments": {}}}]
        history.add(
            Message(role="assistant", content="Let me check", tool_calls=tool_calls)
        )

        formatted = history.get_messages_for_llm(provider="openai")

        # Tool calls should have the 'type' field added
        assert len(formatted[0]["tool_calls"]) == 1
        assert formatted[0]["tool_calls"][0]["id"] == "1"
        assert formatted[0]["tool_calls"][0]["type"] == "function"
        assert formatted[0]["tool_calls"][0]["function"]["name"] == "test"

    def test_format_tool_result_for_openai(self):
        """Test formatting tool results for OpenAI."""
        history = ConversationHistory()

        # Tool messages must follow an assistant message with tool_calls
        tool_calls = [{"id": "call_1", "function": {"name": "test", "arguments": {}}}]
        history.add(
            Message(role="assistant", content="Let me check", tool_calls=tool_calls)
        )

        tool_results = [{"id": "call_1", "output": '{"result": "success"}'}]
        history.add(
            Message(role="tool", content="Result", tool_results=tool_results)
        )

        formatted = history.get_messages_for_llm(provider="openai")

        # Should have assistant message and tool message
        assert len(formatted) == 2
        assert formatted[0]["role"] == "assistant"
        assert formatted[1]["role"] == "tool"
        assert formatted[1]["tool_call_id"] == "call_1"

    def test_get_summary(self):
        """Test getting conversation summary."""
        history = ConversationHistory()

        history.add(Message(role="user", content="What is the status of orders?"))
        history.add(Message(role="assistant", content="Let me check..."))
        history.add(Message(role="user", content="Show me the drift events"))

        summary = history.get_summary()

        assert "Recent topics" in summary
        assert "orders" in summary.lower() or "drift" in summary.lower()

    def test_clear(self):
        """Test clearing history."""
        history = ConversationHistory()

        history.add(Message(role="user", content="Hello"))
        history.add(Message(role="assistant", content="Hi"))

        history.clear()

        assert len(history.messages) == 0

    def test_get_context_window_usage(self):
        """Test getting context window usage stats."""
        history = ConversationHistory(max_messages=20, max_tokens=1000)

        history.add(Message(role="user", content="A" * 100))

        usage = history.get_context_window_usage()

        assert usage["message_count"] == 1
        assert usage["max_messages"] == 20
        assert usage["estimated_tokens"] > 0
        assert usage["usage_percent"] > 0


class TestBuildMessagesForLLM:
    """Tests for the build_messages_for_llm function."""

    def test_build_with_system_prompt(self):
        """Test building messages with system prompt."""
        session_messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
        ]

        messages = build_messages_for_llm(
            session_messages,
            system_prompt="You are a helpful assistant.",
            provider="openai",
        )

        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert len(messages) == 3

    def test_build_respects_max_history(self):
        """Test that max_history is respected."""
        session_messages = [
            Message(role="user", content=f"Message {i}") for i in range(20)
        ]

        messages = build_messages_for_llm(
            session_messages,
            system_prompt="System",
            max_history=5,
        )

        # System + last 5 messages
        assert len(messages) <= 6

    def test_build_for_anthropic(self):
        """Test building messages for Anthropic provider."""
        session_messages = [
            Message(role="user", content="Hello"),
        ]

        messages = build_messages_for_llm(
            session_messages,
            system_prompt="System prompt",
            provider="anthropic",
        )

        # System message should be converted
        assert "[System]" in messages[0]["content"]

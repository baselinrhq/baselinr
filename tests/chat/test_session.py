"""Tests for chat session management."""

from datetime import datetime

import pytest

from baselinr.chat.session import ChatSession, Message


class TestMessage:
    """Tests for the Message class."""

    def test_create_message(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)
        assert msg.tool_calls is None
        assert msg.tool_results is None

    def test_message_with_tool_calls(self):
        """Test creating a message with tool calls."""
        tool_calls = [{"id": "1", "function": {"name": "test", "arguments": {}}}]
        msg = Message(role="assistant", content="", tool_calls=tool_calls)
        assert msg.tool_calls == tool_calls

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = Message(role="user", content="Test message")
        msg_dict = msg.to_dict()

        assert msg_dict["role"] == "user"
        assert msg_dict["content"] == "Test message"
        assert "timestamp" in msg_dict

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "role": "user",
            "content": "Test",
            "timestamp": "2024-01-01T00:00:00",
        }
        msg = Message.from_dict(data)

        assert msg.role == "user"
        assert msg.content == "Test"
        assert isinstance(msg.timestamp, datetime)


class TestChatSession:
    """Tests for the ChatSession class."""

    def test_create_session(self):
        """Test creating a new chat session."""
        session = ChatSession.create(config={"test": True})

        assert len(session.session_id) == 8
        assert session.config == {"test": True}
        assert session.messages == []
        assert isinstance(session.created_at, datetime)

    def test_add_message(self):
        """Test adding messages to session."""
        session = ChatSession.create(config={})

        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"
        assert session.total_messages == 2

    def test_add_message_with_tokens(self):
        """Test adding message with token count."""
        session = ChatSession.create(config={})

        session.add_message("assistant", "Response", tokens_used=100)

        assert session.total_tokens_used == 100

    def test_add_message_with_tool_calls(self):
        """Test adding message with tool calls."""
        session = ChatSession.create(config={})

        tool_calls = [{"id": "1", "function": {"name": "test"}}]
        session.add_message("assistant", "", tool_calls=tool_calls)

        assert session.total_tool_calls == 1

    def test_get_history(self):
        """Test getting conversation history."""
        session = ChatSession.create(config={})

        for i in range(10):
            session.add_message("user", f"Message {i}")

        # Get all history
        history = session.get_history()
        assert len(history) == 10

        # Get last N
        history = session.get_history(last_n=5)
        assert len(history) == 5
        assert history[0].content == "Message 5"

    def test_get_user_messages(self):
        """Test getting only user messages."""
        session = ChatSession.create(config={})

        session.add_message("user", "User 1")
        session.add_message("assistant", "Assistant 1")
        session.add_message("user", "User 2")

        user_msgs = session.get_user_messages()
        assert len(user_msgs) == 2
        assert all(m.role == "user" for m in user_msgs)

    def test_get_assistant_messages(self):
        """Test getting only assistant messages."""
        session = ChatSession.create(config={})

        session.add_message("user", "User 1")
        session.add_message("assistant", "Assistant 1")
        session.add_message("assistant", "Assistant 2")

        assistant_msgs = session.get_assistant_messages()
        assert len(assistant_msgs) == 2
        assert all(m.role == "assistant" for m in assistant_msgs)

    def test_clear_history(self):
        """Test clearing conversation history."""
        session = ChatSession.create(config={})

        session.add_message("user", "Test", tokens_used=50)
        session.add_message("assistant", "Response", tokens_used=100)

        session.clear_history()

        assert len(session.messages) == 0
        assert session.total_messages == 0
        assert session.total_tokens_used == 0

    def test_context_management(self):
        """Test session context management."""
        session = ChatSession.create(config={})

        session.set_context("table", "orders")
        session.set_context("column", "amount")

        assert session.get_context("table") == "orders"
        assert session.get_context("column") == "amount"
        assert session.get_context("missing") is None
        assert session.get_context("missing", "default") == "default"

    def test_get_stats(self):
        """Test getting session statistics."""
        session = ChatSession.create(config={})

        session.add_message("user", "Hello", tokens_used=10)
        session.add_message(
            "assistant",
            "Hi",
            tokens_used=20,
            tool_calls=[{"id": "1"}],
        )

        stats = session.get_stats()

        assert stats["session_id"] == session.session_id
        assert stats["total_messages"] == 2
        assert stats["user_messages"] == 1
        assert stats["assistant_messages"] == 1
        assert stats["total_tokens_used"] == 30
        assert stats["total_tool_calls"] == 1

    def test_to_dict(self):
        """Test converting session to dictionary."""
        session = ChatSession.create(config={"key": "value"})
        session.add_message("user", "Test")

        session_dict = session.to_dict()

        assert session_dict["session_id"] == session.session_id
        assert len(session_dict["messages"]) == 1
        assert "stats" in session_dict

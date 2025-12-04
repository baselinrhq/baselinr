"""Tests for chat renderer."""

import pytest
from io import StringIO
from unittest.mock import MagicMock, patch

from baselinr.chat.renderer import (
    ChatRenderer,
    format_drift_summary,
    format_table_profile,
    format_trend_summary,
)
from baselinr.chat.session import Message


class TestChatRenderer:
    """Tests for the ChatRenderer class."""

    def test_create_renderer(self):
        """Test creating a renderer."""
        renderer = ChatRenderer()
        assert renderer.show_tool_calls is False
        assert renderer.verbose is False

    def test_create_renderer_with_options(self):
        """Test creating a renderer with options."""
        renderer = ChatRenderer(show_tool_calls=True, verbose=True)
        assert renderer.show_tool_calls is True
        assert renderer.verbose is True

    def test_render_user_message_without_rich(self):
        """Test rendering user message without rich library."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_user_message("Hello")

    def test_render_assistant_message_without_rich(self):
        """Test rendering assistant message without rich library."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_assistant_message("Hi there!")

    def test_render_error_without_rich(self):
        """Test rendering error message without rich library."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_error("Something went wrong")

    def test_render_info_without_rich(self):
        """Test rendering info message without rich library."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_info("Information message")

    def test_render_success_without_rich(self):
        """Test rendering success message without rich library."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_success("Operation successful")

    def test_render_warning_without_rich(self):
        """Test rendering warning message without rich library."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_warning("Warning message")

    def test_render_history_empty(self):
        """Test rendering empty history."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_history([])

    def test_render_history_with_messages(self):
        """Test rendering history with messages."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]

        # This should not raise an error
        renderer.render_history(messages)

    def test_render_stats(self):
        """Test rendering session statistics."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        stats = {
            "session_id": "abc123",
            "duration_seconds": 60,
            "total_messages": 10,
            "total_tool_calls": 5,
            "total_tokens_used": 1000,
        }

        # This should not raise an error
        renderer.render_stats(stats)

    def test_render_help(self):
        """Test rendering help message."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_help()

    def test_render_tools(self):
        """Test rendering available tools."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        class MockTool:
            name = "test_tool"
            description = "A test tool"
            category = "test"

        # This should not raise an error
        renderer.render_tools([MockTool()])

    def test_render_tools_empty(self):
        """Test rendering empty tools list."""
        renderer = ChatRenderer()
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_tools([])

    def test_render_tool_call_hidden(self):
        """Test that tool calls are hidden by default."""
        renderer = ChatRenderer(show_tool_calls=False)

        # This should not output anything
        renderer.render_tool_call("test_tool", {"arg": "value"})

    def test_render_tool_call_shown(self):
        """Test that tool calls are shown when enabled."""
        renderer = ChatRenderer(show_tool_calls=True)
        renderer.console = None  # Disable rich

        # This should not raise an error
        renderer.render_tool_call("test_tool", {"arg": "value"})


class TestFormatDriftSummary:
    """Tests for the format_drift_summary function."""

    def test_empty_events(self):
        """Test formatting empty event list."""
        result = format_drift_summary([])
        assert "No drift events found" in result

    def test_single_high_severity(self):
        """Test formatting single high severity event."""
        events = [
            {
                "drift_severity": "high",
                "table_name": "orders",
                "column_name": "amount",
                "metric_name": "mean",
            }
        ]

        result = format_drift_summary(events)

        assert "High Severity" in result
        assert "1 events" in result
        assert "orders" in result

    def test_mixed_severities(self):
        """Test formatting events with mixed severities."""
        events = [
            {"drift_severity": "high", "table_name": "t1", "column_name": "c1", "metric_name": "m1"},
            {"drift_severity": "medium", "table_name": "t2", "column_name": "c2", "metric_name": "m2"},
            {"drift_severity": "low", "table_name": "t3", "column_name": "c3", "metric_name": "m3"},
        ]

        result = format_drift_summary(events)

        assert "High Severity" in result
        assert "Medium Severity" in result
        assert "Low Severity" in result


class TestFormatTableProfile:
    """Tests for the format_table_profile function."""

    def test_format_error(self):
        """Test formatting error response."""
        profile = {"error": "Table not found"}
        result = format_table_profile(profile)

        assert "Error: Table not found" in result

    def test_format_basic_profile(self):
        """Test formatting basic profile."""
        profile = {
            "dataset_name": "orders",
            "schema_name": "public",
            "profiled_at": "2024-01-01T00:00:00",
            "row_count": 10000,
            "column_count": 5,
            "columns": [
                {
                    "column_name": "id",
                    "column_type": "integer",
                    "metrics": {"null_ratio": 0.0},
                },
                {
                    "column_name": "amount",
                    "column_type": "float",
                    "metrics": {"null_ratio": 0.05},
                },
            ],
        }

        result = format_table_profile(profile)

        assert "orders" in result
        assert "public" in result
        assert "10,000" in result
        assert "id" in result
        assert "amount" in result


class TestFormatTrendSummary:
    """Tests for the format_trend_summary function."""

    def test_format_error(self):
        """Test formatting error response."""
        trend_data = {"error": "No data available"}
        result = format_trend_summary(trend_data)

        assert "Error: No data available" in result

    def test_format_basic_trend(self):
        """Test formatting basic trend data."""
        trend_data = {
            "history": [
                {"value": 10, "profiled_at": "2024-01-01"},
                {"value": 12, "profiled_at": "2024-01-02"},
            ],
            "summary": {
                "count": 2,
                "min": 10,
                "max": 12,
                "mean": 11,
                "trend": "increasing",
                "trend_percent": 20.0,
            },
        }

        result = format_trend_summary(trend_data)

        assert "Trend Summary" in result
        assert "2" in result  # count
        assert "increasing" in result

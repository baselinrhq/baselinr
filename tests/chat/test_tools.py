"""Tests for chat tools registry and tool definitions."""

import pytest
from unittest.mock import MagicMock, patch

from baselinr.chat.tools import Tool, ToolRegistry


class TestTool:
    """Tests for the Tool class."""

    def test_create_tool(self):
        """Test creating a tool."""

        def dummy_func(arg1: str) -> str:
            return f"Result: {arg1}"

        tool = Tool(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                },
                "required": ["arg1"],
            },
            function=dummy_func,
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.function == dummy_func
        assert tool.category == "general"

    def test_to_openai_format(self):
        """Test converting tool to OpenAI format."""

        def dummy_func():
            pass

        tool = Tool(
            name="my_tool",
            description="Does something",
            parameters={"type": "object", "properties": {}},
            function=dummy_func,
        )

        openai_format = tool.to_openai_format()

        assert openai_format["type"] == "function"
        assert openai_format["function"]["name"] == "my_tool"
        assert openai_format["function"]["description"] == "Does something"
        assert openai_format["function"]["parameters"] == {
            "type": "object",
            "properties": {},
        }

    def test_to_anthropic_format(self):
        """Test converting tool to Anthropic format."""

        def dummy_func():
            pass

        tool = Tool(
            name="my_tool",
            description="Does something",
            parameters={"type": "object", "properties": {}},
            function=dummy_func,
        )

        anthropic_format = tool.to_anthropic_format()

        assert anthropic_format["name"] == "my_tool"
        assert anthropic_format["description"] == "Does something"
        assert anthropic_format["input_schema"] == {
            "type": "object",
            "properties": {},
        }


class TestToolRegistry:
    """Tests for the ToolRegistry class."""

    def test_create_registry(self):
        """Test creating a tool registry."""
        registry = ToolRegistry()
        assert len(registry.tools) == 0

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()

        tool = Tool(
            name="test",
            description="Test",
            parameters={},
            function=lambda: None,
        )

        registry.register(tool)

        assert "test" in registry.tools
        assert registry.tools["test"] == tool

    def test_get_tool(self):
        """Test getting a tool by name."""
        registry = ToolRegistry()

        tool = Tool(
            name="test",
            description="Test",
            parameters={},
            function=lambda: None,
        )
        registry.register(tool)

        assert registry.get_tool("test") == tool
        assert registry.get_tool("nonexistent") is None

    def test_list_tools(self):
        """Test listing all tools."""
        registry = ToolRegistry()

        for i in range(3):
            registry.register(
                Tool(
                    name=f"tool_{i}",
                    description=f"Tool {i}",
                    parameters={},
                    function=lambda: None,
                )
            )

        tools = registry.list_tools()
        assert len(tools) == 3

    def test_get_tools_by_category(self):
        """Test filtering tools by category."""
        registry = ToolRegistry()

        registry.register(
            Tool(
                name="drift1",
                description="Drift 1",
                parameters={},
                function=lambda: None,
                category="drift",
            )
        )
        registry.register(
            Tool(
                name="profiling1",
                description="Profiling 1",
                parameters={},
                function=lambda: None,
                category="profiling",
            )
        )
        registry.register(
            Tool(
                name="drift2",
                description="Drift 2",
                parameters={},
                function=lambda: None,
                category="drift",
            )
        )

        drift_tools = registry.get_tools_by_category("drift")
        assert len(drift_tools) == 2
        assert all(t.category == "drift" for t in drift_tools)

    def test_to_openai_format(self):
        """Test converting all tools to OpenAI format."""
        registry = ToolRegistry()

        for i in range(2):
            registry.register(
                Tool(
                    name=f"tool_{i}",
                    description=f"Tool {i}",
                    parameters={"type": "object"},
                    function=lambda: None,
                )
            )

        openai_tools = registry.to_openai_format()
        assert len(openai_tools) == 2
        assert all(t["type"] == "function" for t in openai_tools)

    def test_to_anthropic_format(self):
        """Test converting all tools to Anthropic format."""
        registry = ToolRegistry()

        for i in range(2):
            registry.register(
                Tool(
                    name=f"tool_{i}",
                    description=f"Tool {i}",
                    parameters={"type": "object"},
                    function=lambda: None,
                )
            )

        anthropic_tools = registry.to_anthropic_format()
        assert len(anthropic_tools) == 2
        assert all("input_schema" in t for t in anthropic_tools)

    def test_get_tool_descriptions(self):
        """Test getting formatted tool descriptions."""
        registry = ToolRegistry()

        registry.register(
            Tool(
                name="test_tool",
                description="A test tool description",
                parameters={},
                function=lambda: None,
            )
        )

        descriptions = registry.get_tool_descriptions()
        assert "test_tool" in descriptions
        assert "A test tool description" in descriptions


class TestSetupTools:
    """Tests for the setup_tools function."""

    def test_setup_tools_registers_all(self):
        """Test that setup_tools registers all expected tools."""
        from baselinr.chat.tools import setup_tools

        # Create mock engine and config
        mock_engine = MagicMock()

        # Create a mock connection context manager
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        config = {
            "runs_table": "baselinr_runs",
            "results_table": "baselinr_results",
            "events_table": "baselinr_events",
        }

        registry = ToolRegistry()

        # Mock the MetadataQueryClient to avoid actual DB calls
        with patch("baselinr.query.client.MetadataQueryClient"):
            setup_tools(registry, mock_engine, config)

        # Check that expected tools are registered
        expected_tools = [
            "query_recent_runs",
            "query_drift_events",
            "query_anomalies",
            "get_table_profile",
            "get_column_history",
            "compare_runs",
            "search_tables",
            "get_lineage",
        ]

        for tool_name in expected_tools:
            assert registry.get_tool(tool_name) is not None, f"Missing tool: {tool_name}"

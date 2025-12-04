"""
Baselinr Chat Module - Conversational Interface for Data Quality Monitoring.

This module provides a natural language interface for querying and investigating
data quality issues using LLM-powered conversations with tool calling.
"""

from baselinr.chat.agent import ChatAgent
from baselinr.chat.context import ContextEnhancer
from baselinr.chat.history import ConversationHistory
from baselinr.chat.renderer import ChatRenderer
from baselinr.chat.session import ChatSession, Message
from baselinr.chat.tools import Tool, ToolRegistry, setup_tools

__all__ = [
    "ChatSession",
    "Message",
    "ChatAgent",
    "Tool",
    "ToolRegistry",
    "setup_tools",
    "ContextEnhancer",
    "ChatRenderer",
    "ConversationHistory",
]

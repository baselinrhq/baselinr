"""
Pydantic models for Chat API endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # user, assistant, system, tool
    content: str
    timestamp: Optional[datetime] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tokens_used: Optional[int] = None


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    session_id: str
    message: str
    role: str = "assistant"
    timestamp: datetime
    tool_calls_made: int = 0
    tokens_used: Optional[int] = None


class SessionStatsResponse(BaseModel):
    """Statistics for a chat session."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    duration_seconds: float
    total_messages: int
    user_messages: int
    assistant_messages: int
    total_tokens_used: int
    total_tool_calls: int


class ChatHistoryResponse(BaseModel):
    """Chat history for a session."""
    session_id: str
    messages: List[ChatMessage]
    stats: SessionStatsResponse


class ChatConfigResponse(BaseModel):
    """Chat configuration status."""
    enabled: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    max_iterations: int = 5
    max_history_messages: int = 20


class ToolInfo(BaseModel):
    """Information about an available tool."""
    name: str
    description: str
    category: str


class ToolsListResponse(BaseModel):
    """List of available chat tools."""
    tools: List[ToolInfo]

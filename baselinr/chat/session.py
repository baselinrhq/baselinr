"""
Chat session management for Baselinr conversational interface.

Manages conversation state, message history, and session metadata.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class Message:
    """Single message in conversation."""

    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: datetime = field(default_factory=_utcnow)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    tokens_used: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = _utcnow()

        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=timestamp,
            tool_calls=data.get("tool_calls"),
            tool_results=data.get("tool_results"),
            tokens_used=data.get("tokens_used"),
            metadata=data.get("metadata"),
        )


@dataclass
class ChatSession:
    """Manages a single chat session."""

    session_id: str
    config: Dict[str, Any]
    messages: List[Message] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    last_activity: datetime = field(default_factory=_utcnow)

    # Session statistics
    total_tokens_used: int = 0
    total_tool_calls: int = 0
    total_messages: int = 0

    @classmethod
    def create(cls, config: Dict[str, Any]) -> "ChatSession":
        """Create a new chat session with a unique ID."""
        return cls(
            session_id=str(uuid.uuid4())[:8],
            config=config,
        )

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        tokens_used: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Add message to conversation history."""
        message = Message(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            tokens_used=tokens_used,
            metadata=metadata,
        )
        self.messages.append(message)
        self.last_activity = _utcnow()
        self.total_messages += 1

        if tokens_used:
            self.total_tokens_used += tokens_used

        if tool_calls:
            self.total_tool_calls += len(tool_calls)

        return message

    def get_history(self, last_n: Optional[int] = None) -> List[Message]:
        """Get conversation history."""
        if last_n:
            return self.messages[-last_n:]
        return self.messages

    def get_user_messages(self) -> List[Message]:
        """Get only user messages."""
        return [m for m in self.messages if m.role == "user"]

    def get_assistant_messages(self) -> List[Message]:
        """Get only assistant messages."""
        return [m for m in self.messages if m.role == "assistant"]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.messages.clear()
        self.total_tokens_used = 0
        self.total_tool_calls = 0
        self.total_messages = 0

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value for the session."""
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value from the session."""
        return self.context.get(key, default)

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        duration = (_utcnow() - self.created_at).total_seconds()
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "duration_seconds": round(duration, 1),
            "total_messages": self.total_messages,
            "user_messages": len(self.get_user_messages()),
            "assistant_messages": len(self.get_assistant_messages()),
            "total_tokens_used": self.total_tokens_used,
            "total_tool_calls": self.total_tool_calls,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "context": self.context,
            "stats": self.get_stats(),
        }

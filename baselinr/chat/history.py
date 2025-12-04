"""
In-memory conversation history management.

Provides context window management and message formatting for LLM interactions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from baselinr.chat.session import Message


@dataclass
class ConversationHistory:
    """Manages conversation history with context window limits."""

    max_messages: int = 20
    max_tokens: int = 8000  # Approximate token limit for context
    messages: List[Message] = field(default_factory=list)

    def add(self, message: Message) -> None:
        """Add a message and prune if necessary."""
        self.messages.append(message)
        self._prune_if_needed()

    def _prune_if_needed(self) -> None:
        """Prune old messages to stay within limits."""
        # Keep at most max_messages
        if len(self.messages) > self.max_messages:
            # Keep the system message if present, plus recent messages
            system_messages = [m for m in self.messages if m.role == "system"]
            other_messages = [m for m in self.messages if m.role != "system"]

            # Keep the most recent messages
            keep_count = self.max_messages - len(system_messages)
            self.messages = system_messages + other_messages[-keep_count:]

    def get_messages_for_llm(self, provider: str = "openai") -> List[Dict[str, Any]]:
        """
        Format messages for LLM API.

        Args:
            provider: LLM provider ('openai' or 'anthropic')

        Returns:
            List of formatted messages
        """
        formatted = []

        if provider == "openai":
            # For OpenAI, ensure proper pairing of assistant messages with tool_calls
            # and their corresponding tool messages
            # Tool messages MUST immediately follow an assistant message with tool_calls
            i = 0
            while i < len(self.messages):
                msg = self.messages[i]

                # Check if this is an assistant message with tool_calls
                if msg.role == "assistant" and msg.tool_calls:
                    # Add the assistant message
                    formatted.append(self._format_for_openai(msg))
                    i += 1

                    # Add all following tool messages until we hit a non-tool message
                    # Only include tool messages with valid tool_call_ids
                    while i < len(self.messages) and self.messages[i].role == "tool":
                        tool_msg = self.messages[i]
                        # Validate tool message has a valid tool_call_id
                        if tool_msg.tool_results and len(tool_msg.tool_results) > 0:
                            tool_call_id = tool_msg.tool_results[0].get("id", "")
                            if tool_call_id:
                                formatted.append(self._format_for_openai(tool_msg))
                        i += 1
                elif msg.role == "tool":
                    # Skip orphaned tool messages
                    # (not immediately following assistant with tool_calls)
                    # This can happen if messages get out of order or history is filtered
                    i += 1
                    continue
                else:
                    # Regular message (user, system, or assistant without tool_calls)
                    formatted.append(self._format_for_openai(msg))
                    i += 1
        else:
            # For Anthropic, just format all messages
            for msg in self.messages:
                formatted.append(self._format_for_anthropic(msg))

        return formatted

    def _format_for_openai(self, msg: Message) -> Dict[str, Any]:
        """Format message for OpenAI API."""
        base: Dict[str, Any] = {"role": msg.role, "content": msg.content}

        if msg.tool_calls:
            # Ensure each tool call has the required 'type' field
            formatted_tool_calls = []
            for call in msg.tool_calls:
                formatted_call = dict(call)  # Make a copy
                # Always set type to "function" for OpenAI API compatibility
                formatted_call["type"] = "function"
                formatted_tool_calls.append(formatted_call)
            base["tool_calls"] = formatted_tool_calls

        if msg.role == "tool":
            # Tool responses need special handling
            if msg.tool_results and len(msg.tool_results) > 0:
                tool_call_id = msg.tool_results[0].get("id", "")
                if not tool_call_id:
                    # Fallback: try to get from content if structured differently
                    tool_call_id = ""
                base["tool_call_id"] = tool_call_id
                base["content"] = msg.tool_results[0].get("output", msg.content)
            else:
                # Tool message without tool_results - use content as-is
                base["tool_call_id"] = ""
                base["content"] = msg.content or ""

        return base

    def _format_for_anthropic(self, msg: Message) -> Dict[str, Any]:
        """Format message for Anthropic API."""
        if msg.role == "system":
            # Anthropic handles system messages differently
            return {"role": "user", "content": f"[System]: {msg.content}"}

        base: Dict[str, Any] = {"role": msg.role, "content": msg.content}

        if msg.tool_calls:
            # Anthropic uses tool_use content blocks
            base["content"] = [{"type": "text", "text": msg.content or ""}] + [
                {
                    "type": "tool_use",
                    "id": call.get("id"),
                    "name": call.get("function", {}).get("name"),
                    "input": call.get("function", {}).get("arguments", {}),
                }
                for call in msg.tool_calls
            ]

        return base

    def get_summary(self) -> str:
        """Get a summary of the conversation for context."""
        user_messages = [m for m in self.messages if m.role == "user"]
        if not user_messages:
            return "No conversation history."

        topics = []
        for msg in user_messages[-5:]:  # Last 5 user messages
            # Extract first 50 chars as topic indicator
            topic = msg.content[:50].replace("\n", " ")
            if len(msg.content) > 50:
                topic += "..."
            topics.append(topic)

        return "Recent topics: " + "; ".join(topics)

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def get_context_window_usage(self) -> Dict[str, Any]:
        """Get current context window usage statistics."""
        total_chars = sum(len(m.content) for m in self.messages)
        estimated_tokens = total_chars // 4  # Rough estimate

        return {
            "message_count": len(self.messages),
            "max_messages": self.max_messages,
            "estimated_tokens": estimated_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": round((estimated_tokens / self.max_tokens) * 100, 1),
        }


def build_messages_for_llm(
    session_messages: List[Message],
    system_prompt: str,
    provider: str = "openai",
    max_history: int = 20,
) -> List[Dict[str, Any]]:
    """
    Build message list for LLM API from session messages.

    Args:
        session_messages: Messages from the chat session
        system_prompt: System prompt to include
        provider: LLM provider ('openai' or 'anthropic')
        max_history: Maximum number of historical messages to include

    Returns:
        Formatted message list for LLM API
    """
    history = ConversationHistory(max_messages=max_history)

    # Add system prompt first
    history.add(Message(role="system", content=system_prompt))

    # Add session messages
    for msg in session_messages[-max_history:]:
        history.add(msg)

    return history.get_messages_for_llm(provider)

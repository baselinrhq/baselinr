"""
Chat API routes for Baselinr Dashboard.

Provides endpoints for the conversational interface.
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy.engine import Engine

from chat_models import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatConfigResponse,
    SessionStatsResponse,
    ChatMessage,
    ToolsListResponse,
    ToolInfo,
)

# Add parent directory to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Lazy imports for baselinr chat
CHAT_AVAILABLE = False
agent_instance = None
sessions: Dict[str, object] = {}  # In-memory session storage


def _init_chat_agent(engine: Engine, config: dict):
    """Initialize the chat agent lazily."""
    global CHAT_AVAILABLE, agent_instance

    try:
        from baselinr.chat.agent import AgentConfig, create_agent

        # Check if LLM is configured
        llm_config = config.get("llm", {})
        if not llm_config.get("enabled"):
            return False

        # Create agent configuration
        agent_config = AgentConfig(
            max_iterations=llm_config.get("chat", {}).get("max_iterations", 5),
            max_history_messages=llm_config.get("chat", {}).get("max_history_messages", 20),
            tool_timeout=llm_config.get("chat", {}).get("tool_timeout", 30),
        )

        # Storage config
        storage_config = {
            "runs_table": config.get("storage", {}).get("runs_table", "baselinr_runs"),
            "results_table": config.get("storage", {}).get("results_table", "baselinr_results"),
            "events_table": "baselinr_events",
        }

        # Create the agent
        agent_instance = create_agent(
            llm_config=llm_config,
            storage_engine=engine,
            storage_config=storage_config,
            agent_config=agent_config,
        )

        CHAT_AVAILABLE = True
        return True

    except Exception as e:
        print(f"Failed to initialize chat agent: {e}")
        CHAT_AVAILABLE = False
        return False


def _get_or_create_session(session_id: Optional[str]):
    """Get existing session or create a new one."""
    from baselinr.chat.session import ChatSession

    if session_id and session_id in sessions:
        return sessions[session_id]

    # Create new session
    new_session = ChatSession.create(config={})
    sessions[new_session.session_id] = new_session
    return new_session


def register_chat_routes(app, engine: Engine, config: dict):
    """
    Register chat API routes.

    Args:
        app: FastAPI application
        engine: SQLAlchemy engine for database access
        config: Application configuration dictionary
    """
    router = APIRouter(prefix="/api/chat", tags=["chat"])

    # Try to initialize chat agent
    _init_chat_agent(engine, config)

    @router.get("/config", response_model=ChatConfigResponse)
    async def get_chat_config():
        """
        Get chat configuration status.

        Returns whether chat is available and the configuration.
        """
        llm_config = config.get("llm", {})

        return ChatConfigResponse(
            enabled=CHAT_AVAILABLE,
            provider=llm_config.get("provider") if CHAT_AVAILABLE else None,
            model=llm_config.get("model") if CHAT_AVAILABLE else None,
            max_iterations=llm_config.get("chat", {}).get("max_iterations", 5),
            max_history_messages=llm_config.get("chat", {}).get("max_history_messages", 20),
        )

    @router.post("/message", response_model=ChatResponse)
    async def send_message(request: ChatRequest):
        """
        Send a message to the chat agent.

        Creates a new session if session_id is not provided.
        """
        if not CHAT_AVAILABLE or agent_instance is None:
            raise HTTPException(
                status_code=503,
                detail="Chat is not available. Please configure LLM in your settings.",
            )

        try:
            import asyncio

            # Get or create session
            session = _get_or_create_session(request.session_id)

            # Process message (use async version if available)
            try:
                response_text = await agent_instance.process_message_async(
                    request.message, session
                )
            except Exception:
                # Fall back to sync method run in executor
                loop = asyncio.get_event_loop()
                response_text = await loop.run_in_executor(
                    None,
                    lambda: agent_instance.process_message(request.message, session)
                )

            # Get the last assistant message for metadata
            last_msg = session.messages[-1] if session.messages else None
            tool_calls_count = 0
            tokens = None

            if last_msg and last_msg.role == "assistant":
                tokens = last_msg.tokens_used
                if last_msg.metadata:
                    tool_calls_count = last_msg.metadata.get("tool_calls", 0)

            return ChatResponse(
                session_id=session.session_id,
                message=response_text,
                role="assistant",
                timestamp=datetime.now(timezone.utc),
                tool_calls_made=tool_calls_count,
                tokens_used=tokens,
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

    @router.get("/history/{session_id}", response_model=ChatHistoryResponse)
    async def get_chat_history(session_id: str):
        """
        Get chat history for a session.
        """
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session = sessions[session_id]
        stats = session.get_stats()

        messages = [
            ChatMessage(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                tool_calls=msg.tool_calls,
                tokens_used=msg.tokens_used,
            )
            for msg in session.messages
        ]

        return ChatHistoryResponse(
            session_id=session_id,
            messages=messages,
            stats=SessionStatsResponse(
                session_id=stats["session_id"],
                created_at=datetime.fromisoformat(stats["created_at"]),
                last_activity=datetime.fromisoformat(stats["last_activity"]),
                duration_seconds=stats["duration_seconds"],
                total_messages=stats["total_messages"],
                user_messages=stats["user_messages"],
                assistant_messages=stats["assistant_messages"],
                total_tokens_used=stats["total_tokens_used"],
                total_tool_calls=stats["total_tool_calls"],
            ),
        )

    @router.delete("/session/{session_id}")
    async def clear_session(session_id: str):
        """
        Clear a chat session.
        """
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        session = sessions[session_id]
        session.clear_history()

        if agent_instance:
            agent_instance.clear_cache()

        return {"status": "cleared", "session_id": session_id}

    @router.get("/tools", response_model=ToolsListResponse)
    async def list_tools():
        """
        List available chat tools.
        """
        if not CHAT_AVAILABLE or agent_instance is None:
            raise HTTPException(status_code=503, detail="Chat is not available")

        tools = [
            ToolInfo(
                name=tool.name,
                description=tool.description,
                category=tool.category,
            )
            for tool in agent_instance.tools.list_tools()
        ]

        return ToolsListResponse(tools=tools)

    @router.get("/sessions")
    async def list_sessions():
        """
        List active chat sessions.
        """
        return {
            "sessions": [
                {
                    "session_id": sid,
                    "message_count": len(session.messages),
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                }
                for sid, session in sessions.items()
            ]
        }

    # Register router
    app.include_router(router)

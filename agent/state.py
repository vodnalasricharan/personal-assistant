from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    """Mutable state passed through the LangGraph agent graph."""

    messages: list[dict[str, str]] = field(default_factory=list)
    """Full conversation history [{role, content}, ...]"""

    user_input: str = ""
    """Latest raw user message."""

    user_intent: str = ""
    """Classified intent: knowledge_query | generate_* | general_conversation"""

    retrieved_context: str = ""
    """Concatenated text from RAG retrieval."""

    retrieved_sources: list[str] = field(default_factory=list)
    """Source file names from retrieved chunks."""

    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    """Raw retrieved chunks for expandable UI display."""

    tool_results: list[dict[str, Any]] = field(default_factory=list)
    """Results from executed tools."""

    pending_email: dict[str, Any] | None = None
    """Staged email awaiting user confirmation."""

    generated_file_path: str | None = None
    """Path to a generated file (PPT, DOCX, PDF)."""

    final_response: str = ""
    """Final answer to return to the user."""

    error: str | None = None
    """Error message if something went wrong."""

    needs_confirmation: bool = False
    """Whether the next action requires explicit user confirmation."""

    conversation_id: str = ""
    """Active conversation id for memory persistence."""

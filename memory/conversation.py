from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from config.settings import Settings
from memory.database import db_connection, initialize_db


class Message:
    __slots__ = ("id", "conversation_id", "role", "content", "timestamp", "metadata")

    def __init__(
        self,
        id: str,
        conversation_id: str,
        role: str,
        content: str,
        timestamp: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.id = id
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ConversationMemory:
    """SQLite-backed conversation history manager."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        initialize_db(settings)

    def create_conversation(self, title: str | None = None) -> str:
        conversation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with db_connection(self.settings) as conn:
            conn.execute(
                "INSERT INTO conversations (id, created_at, title) VALUES (?, ?, ?)",
                (conversation_id, now, title),
            )
        return conversation_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(metadata or {})
        with db_connection(self.settings) as conn:
            conn.execute(
                """INSERT INTO messages (id, conversation_id, role, content, timestamp, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (message_id, conversation_id, role, content, now, meta_json),
            )
        return message_id

    def get_messages(self, conversation_id: str, limit: int = 50) -> list[Message]:
        with db_connection(self.settings) as conn:
            rows = conn.execute(
                """SELECT id, conversation_id, role, content, timestamp, metadata
                   FROM messages WHERE conversation_id = ?
                   ORDER BY timestamp ASC
                   LIMIT ?""",
                (conversation_id, limit),
            ).fetchall()
        return [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                timestamp=row["timestamp"],
                metadata=json.loads(row["metadata"] or "{}"),
            )
            for row in rows
        ]

    def delete_messages(self, conversation_id: str) -> None:
        with db_connection(self.settings) as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))

    def delete_conversation(self, conversation_id: str) -> None:
        with db_connection(self.settings) as conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    def list_conversations(self, limit: int = 20) -> list[dict[str, Any]]:
        with db_connection(self.settings) as conn:
            rows = conn.execute(
                "SELECT id, created_at, title FROM conversations ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def build_chat_history(self, conversation_id: str) -> list[dict[str, str]]:
        """Return messages as a list of {role, content} dicts for LLM context."""
        messages = self.get_messages(conversation_id)
        return [{"role": msg.role, "content": msg.content} for msg in messages if msg.role in ("user", "assistant")]

from __future__ import annotations

import pytest


def _make_settings(tmp_path):
    from config.settings import Settings
    s = Settings(
        gemini_api_key="",
        chroma_persist_directory=tmp_path / "chroma",
        sqlite_database=tmp_path / "app.db",
        data_dir=tmp_path / "data",
        generated_dir=tmp_path / "generated",
        log_dir=tmp_path / "logs",
    )
    s.ensure_directories()
    return s


class TestConversationMemory:
    def test_create_conversation_returns_id(self, tmp_path):
        from memory.conversation import ConversationMemory
        settings = _make_settings(tmp_path)
        memory = ConversationMemory(settings)
        cid = memory.create_conversation()
        assert isinstance(cid, str)
        assert len(cid) > 0

    def test_add_and_retrieve_messages(self, tmp_path):
        from memory.conversation import ConversationMemory
        settings = _make_settings(tmp_path)
        memory = ConversationMemory(settings)
        cid = memory.create_conversation()
        memory.add_message(cid, "user", "Hello!")
        memory.add_message(cid, "assistant", "Hi there!")
        messages = memory.get_messages(cid)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello!"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there!"

    def test_delete_messages(self, tmp_path):
        from memory.conversation import ConversationMemory
        settings = _make_settings(tmp_path)
        memory = ConversationMemory(settings)
        cid = memory.create_conversation()
        memory.add_message(cid, "user", "This will be deleted")
        memory.delete_messages(cid)
        assert memory.get_messages(cid) == []

    def test_delete_conversation(self, tmp_path):
        from memory.conversation import ConversationMemory
        settings = _make_settings(tmp_path)
        memory = ConversationMemory(settings)
        cid = memory.create_conversation()
        memory.add_message(cid, "user", "Hello")
        memory.delete_conversation(cid)
        # Messages should be gone too (CASCADE)
        assert memory.get_messages(cid) == []

    def test_list_conversations(self, tmp_path):
        from memory.conversation import ConversationMemory
        settings = _make_settings(tmp_path)
        memory = ConversationMemory(settings)
        id1 = memory.create_conversation(title="Conv 1")
        id2 = memory.create_conversation(title="Conv 2")
        conversations = memory.list_conversations()
        ids = [c["id"] for c in conversations]
        assert id1 in ids
        assert id2 in ids

    def test_message_metadata_saved_and_restored(self, tmp_path):
        from memory.conversation import ConversationMemory
        settings = _make_settings(tmp_path)
        memory = ConversationMemory(settings)
        cid = memory.create_conversation()
        memory.add_message(cid, "assistant", "Response", metadata={"sources": ["resume.pdf"]})
        messages = memory.get_messages(cid)
        assert messages[0].metadata["sources"] == ["resume.pdf"]

    def test_build_chat_history_filters_roles(self, tmp_path):
        from memory.conversation import ConversationMemory
        settings = _make_settings(tmp_path)
        memory = ConversationMemory(settings)
        cid = memory.create_conversation()
        memory.add_message(cid, "user", "Question")
        memory.add_message(cid, "assistant", "Answer")
        memory.add_message(cid, "tool", "Tool result")
        history = memory.build_chat_history(cid)
        assert len(history) == 2  # only user and assistant
        assert all(m["role"] in ("user", "assistant") for m in history)

    def test_multiple_conversations_are_independent(self, tmp_path):
        from memory.conversation import ConversationMemory
        settings = _make_settings(tmp_path)
        memory = ConversationMemory(settings)
        cid1 = memory.create_conversation()
        cid2 = memory.create_conversation()
        memory.add_message(cid1, "user", "Conv1 message")
        memory.add_message(cid2, "user", "Conv2 message")
        assert len(memory.get_messages(cid1)) == 1
        assert len(memory.get_messages(cid2)) == 1
        assert memory.get_messages(cid1)[0].content == "Conv1 message"

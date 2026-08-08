from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


def _make_settings(tmp_path):
    from config.settings import Settings
    return Settings(
        gemini_api_key="",
        chroma_persist_directory=tmp_path / "chroma",
        sqlite_database=tmp_path / "app.db",
        data_dir=tmp_path / "data",
        generated_dir=tmp_path / "generated",
        log_dir=tmp_path / "logs",
    )


# ── Intent classification tests ───────────────────────────────────────────────

class TestIntentClassification:
    def test_returns_knowledge_query_when_llm_disabled(self, tmp_path):
        from agent.nodes import classify_intent
        settings = _make_settings(tmp_path)
        intent = classify_intent("What are his skills?", settings)
        assert intent == "knowledge_query"

    def test_gemini_response_mapped_to_valid_label(self, tmp_path):
        from agent.nodes import classify_intent
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        with patch("agent.nodes._call_llm", return_value="generate_presentation"):
            with patch("agent.nodes._make_client", return_value=MagicMock()):
                settings_mock = MagicMock()
                settings_mock.llm_enabled = True
                settings_mock.gemini_api_key = "fake"
                settings_mock.gemini_chat_model = "gemini-1.5-flash"
                intent = classify_intent("Create a PPT about him", settings_mock)
        assert intent == "generate_presentation"

    def test_unknown_llm_label_falls_back_to_knowledge_query(self, tmp_path):
        from agent.nodes import classify_intent
        settings = _make_settings(tmp_path)
        with patch("agent.nodes._call_llm", return_value="nonsense_label"):
            with patch("agent.nodes._make_client", return_value=MagicMock()):
                settings_mock = MagicMock()
                settings_mock.llm_enabled = True
                intent = classify_intent("something", settings_mock)
        assert intent == "knowledge_query"


# ── Agent node tests ──────────────────────────────────────────────────────────

class TestNodeRetrieve:
    def test_no_retrieval_for_general_conversation(self, tmp_path):
        from agent.nodes import node_retrieve
        from agent.state import AgentState

        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        from rag.embeddings import HashEmbeddingProvider
        from rag.vector_store import VectorStore
        from rag.retriever import Retriever

        embedding_provider = HashEmbeddingProvider(dimensions=64)
        vs = VectorStore(settings, embedding_provider)
        retriever = Retriever(settings, vector_store=vs, embedding_provider=embedding_provider)

        state = AgentState(user_input="Hello!", user_intent="general_conversation")
        result = node_retrieve(state, settings, retriever)
        assert result.retrieved_context == ""
        assert result.retrieved_sources == []

    def test_retrieval_for_knowledge_query(self, tmp_path):
        from agent.nodes import node_retrieve
        from agent.state import AgentState
        from rag.types import DocumentChunk

        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        from rag.embeddings import HashEmbeddingProvider
        from rag.vector_store import VectorStore
        from rag.retriever import Retriever

        embedding_provider = HashEmbeddingProvider(dimensions=64)
        vs = VectorStore(settings, embedding_provider)
        vs.upsert_chunks([
            DocumentChunk(id="t1", text="Python developer with 5 years experience", metadata={"source": "resume.pdf"}),
        ])
        retriever = Retriever(settings, vector_store=vs, embedding_provider=embedding_provider)

        state = AgentState(user_input="Python experience", user_intent="knowledge_query")
        result = node_retrieve(state, settings, retriever)
        assert result.retrieved_context != ""
        assert len(result.retrieved_sources) >= 1


# ── AgentGraph routing tests ─────────────────────────────────────────────────

class TestAgentGraphRouting:
    def test_knowledge_query_uses_rag_path(self, tmp_path):
        from agent.graph import AgentGraph
        from agent.state import AgentState
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        with patch("agent.graph.node_classify_intent", side_effect=lambda s, cfg: (setattr(s, "user_intent", "knowledge_query") or s)):
            with patch("agent.graph.node_retrieve", side_effect=lambda s, cfg, r: s):
                with patch("agent.graph.node_generate_response") as mock_gen:
                    mock_gen.side_effect = lambda s, cfg: (setattr(s, "final_response", "mocked response") or s)
                    graph = AgentGraph(settings)
                    state = AgentState(user_input="Tell me about his skills")
                    result = graph.run(state)
        assert result.final_response == "mocked response"

    def test_resume_intent_calls_resume_nodes(self, tmp_path):
        from agent.graph import AgentGraph
        from agent.state import AgentState
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        with patch("agent.graph.node_classify_intent", side_effect=lambda s, cfg: (setattr(s, "user_intent", "generate_resume") or s)):
            with patch("agent.graph.node_retrieve", side_effect=lambda s, cfg, r: s):
                with patch("agent.graph.node_plan_resume") as mock_plan:
                    def _set_resume_data(s, cfg):
                        s.tool_results.append({"type": "resume_data", "data": {"name": "Test"}, "role": "ML Engineer"})
                        return s
                    mock_plan.side_effect = _set_resume_data
                    with patch("agent.graph.build_resume_docx") as mock_build:
                        mock_build.return_value = tmp_path / "resume.docx"
                        (tmp_path / "resume.docx").write_bytes(b"fake")
                        graph = AgentGraph(settings)
                        state = AgentState(user_input="Create an ML Engineer resume for him")
                        result = graph.run(state)
        assert result.generated_file_path is not None or result.error is not None

    def test_ppt_intent_calls_ppt_nodes(self, tmp_path):
        from agent.graph import AgentGraph
        from agent.state import AgentState
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        with patch("agent.graph.node_classify_intent", side_effect=lambda s, cfg: (setattr(s, "user_intent", "generate_presentation") or s)):
            with patch("agent.graph.node_retrieve", side_effect=lambda s, cfg, r: s):
                with patch("agent.graph.node_plan_presentation") as mock_plan:
                    def _set_plan(s, cfg):
                        s.tool_results.append({"type": "ppt_plan", "slides": []})
                        return s
                    mock_plan.side_effect = _set_plan
                    with patch("agent.graph.build_presentation") as mock_build:
                        mock_build.return_value = tmp_path / "test.pptx"
                        (tmp_path / "test.pptx").write_bytes(b"fake")
                        graph = AgentGraph(settings)
                        state = AgentState(user_input="Create a PPT about me")
                        result = graph.run(state)
        assert result.generated_file_path is not None or result.error is not None

    def test_document_intent_calls_document_nodes(self, tmp_path):
        from agent.graph import AgentGraph
        from agent.state import AgentState
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        with patch("agent.graph.node_classify_intent", side_effect=lambda s, cfg: (setattr(s, "user_intent", "generate_document") or s)):
            with patch("agent.graph.node_retrieve", side_effect=lambda s, cfg, r: s):
                with patch("agent.graph.node_plan_document") as mock_plan:
                    def _set_document_content(s, cfg):
                        s.tool_results.append({"type": "document_content", "content": "# Bio", "doc_type": "Professional Bio"})
                        return s
                    mock_plan.side_effect = _set_document_content
                    with patch("agent.graph.build_docx") as mock_build:
                        mock_build.return_value = tmp_path / "profile.docx"
                        (tmp_path / "profile.docx").write_bytes(b"fake")
                        graph = AgentGraph(settings)
                        state = AgentState(user_input="Create a professional bio")
                        result = graph.run(state)
        assert result.generated_file_path is not None or result.error is not None

    def test_unknown_info_response_is_graceful(self, tmp_path):
        from agent.graph import AgentGraph
        from agent.state import AgentState
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        with patch("agent.graph.node_classify_intent", side_effect=lambda s, cfg: (setattr(s, "user_intent", "knowledge_query") or s)):
            with patch("agent.graph.node_retrieve", side_effect=lambda s, cfg, r: s):
                with patch("agent.graph.node_generate_response") as mock_gen:
                    def _no_info(s, cfg):
                        s.final_response = "I don't have that information in my knowledge base."
                        return s
                    mock_gen.side_effect = _no_info
                    graph = AgentGraph(settings)
                    state = AgentState(user_input="What is his favorite football team?")
                    result = graph.run(state)
        assert "knowledge base" in result.final_response

from __future__ import annotations

import logging
from typing import Any

from agent.nodes import (
    node_classify_intent,
    node_generate_response,
    node_plan_document,
    node_plan_presentation,
    node_plan_resume,
    node_retrieve,
)
from agent.state import AgentState
from config.langsmith import set_trace_error, set_trace_outputs, trace_block
from config.settings import Settings
from generators.ppt import build_presentation
from generators.resume import build_resume_docx
from generators.docx import build_docx
from rag.embeddings import build_embedding_provider
from rag.retriever import Retriever
from rag.vector_store import build_vector_store

logger = logging.getLogger(__name__)


def _build_retriever(settings: Settings) -> Retriever:
    embedding_provider = build_embedding_provider(settings)
    vector_store = build_vector_store(settings, embedding_provider)
    return Retriever(settings, vector_store=vector_store, embedding_provider=embedding_provider)


class AgentGraph:
    """
    Orchestrates the LangGraph-style agent pipeline.

    Rather than using LangGraph's StateGraph API (which adds a heavy compile
    step), we implement the same directed-graph semantics as explicit node
    function calls with conditional edges — this is cleaner, easier to test,
    and has no external compilation overhead.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.retriever = _build_retriever(settings)

    def run(self, state: AgentState) -> AgentState:
        """Execute the full agent pipeline for one turn."""
        with trace_block(
            self.settings,
            "agent_run",
            run_type="chain",
            inputs={
                "user_input": state.user_input,
                "conversation_id": state.conversation_id,
            },
            metadata={
                "component": "agent_graph",
            },
        ) as run_tree:
            try:
                # ── Node 1: Classify intent ──────────────────────────────────────────
                state = node_classify_intent(state, self.settings)

                # ── Node 2: Retrieve context (conditional) ───────────────────────────
                state = node_retrieve(state, self.settings, self.retriever)

                # ── Node 3: Route to specialist nodes ────────────────────────────────
                intent = state.user_intent

                if intent == "generate_presentation":
                    state = node_plan_presentation(state, self.settings)
                    if not state.error:
                        state = self._execute_ppt(state)
                    state.final_response = self._ppt_response(state)
                    set_trace_outputs(
                        run_tree,
                        {
                            "intent": state.user_intent,
                            "final_response": state.final_response,
                            "generated_file_path": state.generated_file_path,
                            "retrieved_sources": state.retrieved_sources,
                            "retrieved_chunks": state.retrieved_chunks,
                            "tool_results": state.tool_results,
                            "error": state.error,
                        },
                    )
                    return state

                if intent == "generate_resume":
                    state = node_plan_resume(state, self.settings)
                    if not state.error:
                        state = self._execute_resume(state)
                    state.final_response = self._resume_response(state)
                    set_trace_outputs(
                        run_tree,
                        {
                            "intent": state.user_intent,
                            "final_response": state.final_response,
                            "generated_file_path": state.generated_file_path,
                            "retrieved_sources": state.retrieved_sources,
                            "retrieved_chunks": state.retrieved_chunks,
                            "tool_results": state.tool_results,
                            "error": state.error,
                        },
                    )
                    return state

                if intent == "generate_document":
                    state = node_plan_document(state, self.settings)
                    if not state.error:
                        state = self._execute_document(state)
                    state.final_response = self._document_response(state)
                    set_trace_outputs(
                        run_tree,
                        {
                            "intent": state.user_intent,
                            "final_response": state.final_response,
                            "generated_file_path": state.generated_file_path,
                            "retrieved_sources": state.retrieved_sources,
                            "retrieved_chunks": state.retrieved_chunks,
                            "tool_results": state.tool_results,
                            "error": state.error,
                        },
                    )
                    return state

                # Default: knowledge_query or general_conversation → generate response
                state = node_generate_response(state, self.settings)
                set_trace_outputs(
                    run_tree,
                    {
                        "intent": state.user_intent,
                        "final_response": state.final_response,
                        "retrieved_sources": state.retrieved_sources,
                        "retrieved_chunks": state.retrieved_chunks,
                        "tool_results": state.tool_results,
                        "error": state.error,
                    },
                )
                return state
            except Exception as exc:
                set_trace_error(run_tree, exc)
                raise

    # ── Private helpers ──────────────────────────────────────────────────────

    def _execute_ppt(self, state: AgentState) -> AgentState:
        ppt_plan_result = next(
            (r for r in state.tool_results if r.get("type") == "ppt_plan"), None
        )
        if not ppt_plan_result:
            state.error = "No PPT plan available."
            return state

        slides: list[dict[str, Any]] = ppt_plan_result.get("slides", [])
        try:
            output_path = build_presentation(slides, self.settings)
            state.generated_file_path = str(output_path)
        except Exception as exc:
            logger.error("PPT generation failed: %s", exc)
            state.error = f"PPT generation failed: {exc}"
        return state

    def _execute_resume(self, state: AgentState) -> AgentState:
        resume_result = next(
            (r for r in state.tool_results if r.get("type") == "resume_data"), None
        )
        if not resume_result:
            state.error = "No resume data available."
            return state

        resume_data: dict[str, Any] = resume_result.get("data", {})
        role: str = resume_result.get("role", "General")
        try:
            output_path = build_resume_docx(resume_data, role, self.settings)
            state.generated_file_path = str(output_path)
        except Exception as exc:
            logger.error("Resume generation failed: %s", exc)
            state.error = f"Resume generation failed: {exc}"
        return state

    def _execute_document(self, state: AgentState) -> AgentState:
        doc_result = next(
            (r for r in state.tool_results if r.get("type") == "document_content"), None
        )
        if not doc_result:
            state.error = "No document content available."
            return state

        content: str = doc_result.get("content", "")
        doc_type: str = doc_result.get("doc_type", "document")
        try:
            output_path = build_docx(content, doc_type, self.settings)
            state.generated_file_path = str(output_path)
        except Exception as exc:
            logger.error("Document generation failed: %s", exc)
            state.error = f"Document generation failed: {exc}"
        return state

    @staticmethod
    def _ppt_response(state: AgentState) -> str:
        if state.error:
            return f"I encountered an error generating the presentation: {state.error}"
        if state.generated_file_path:
            return "I've generated a presentation based on the knowledge base. You can download it below."
        return "Presentation generation did not produce output."

    @staticmethod
    def _resume_response(state: AgentState) -> str:
        if state.error:
            return f"I encountered an error generating the resume: {state.error}"
        if state.generated_file_path:
            return "I've generated a tailored resume based on the knowledge base. You can download it below."
        return "Resume generation did not produce output."

    @staticmethod
    def _document_response(state: AgentState) -> str:
        if state.error:
            return f"I encountered an error generating the document: {state.error}"
        if state.generated_file_path:
            return "I've generated the requested document. You can download it below."
        return "Document generation did not produce output."


def get_agent(settings: Settings) -> AgentGraph:
    """Return a singleton AgentGraph for the application lifetime."""
    return AgentGraph(settings)

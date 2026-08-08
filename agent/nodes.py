from __future__ import annotations

import json
import logging
import time
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from agent.prompts import (
    AGENT_SYSTEM_PROMPT,
    INTENT_CLASSIFIER_PROMPT,
    PPT_STRUCTURE_PROMPT,
    RAG_SYSTEM_PROMPT,
    RESUME_TAILOR_PROMPT,
    DOCUMENT_GENERATION_PROMPT,
)
from agent.state import AgentState
from config.langsmith import set_trace_error, set_trace_outputs, trace_block
from config.settings import Settings
from rag.retriever import Retriever

logger = logging.getLogger(__name__)

INTENT_LABELS = {
    "knowledge_query",
    "generate_presentation",
    "generate_resume",
    "generate_document",
    "general_conversation",
}


def _make_client(settings: Settings) -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=8),
    reraise=True,
)
def _call_llm(client: genai.Client, model_name: str, prompt: str, system: str = "") -> str:
    contents: list[genai_types.Content] = [
        genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
    ]
    config = genai_types.GenerateContentConfig(
        system_instruction=system or AGENT_SYSTEM_PROMPT,
    )
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=config,
    )
    return response.text or ""


def _is_retryable_llm_error(exc: Exception) -> bool:
    if isinstance(exc, RetryError):
        last_exc = exc.last_attempt.exception()
        if isinstance(last_exc, Exception):
            exc = last_exc
    return isinstance(exc, genai_errors.ClientError)



def classify_intent(user_message: str, settings: Settings) -> str:
    """Classify user intent using Gemini."""
    if not settings.llm_enabled:
        return "knowledge_query"

    prompt = INTENT_CLASSIFIER_PROMPT.format(message=user_message)
    try:
        client = _make_client(settings)
        raw = _call_llm(client, settings.gemini_chat_model, prompt).strip().strip('"').lower()
        return raw if raw in INTENT_LABELS else "knowledge_query"
    except Exception as exc:
        if _is_retryable_llm_error(exc):
            logger.warning("Intent classification failed with Gemini client error: %s", exc)
        else:
            logger.warning("Intent classification failed: %s", exc)
        return "knowledge_query"


def node_classify_intent(state: AgentState, settings: Settings) -> AgentState:
    """LangGraph node: classify the user intent."""
    classifier_prompt = INTENT_CLASSIFIER_PROMPT.format(message=state.user_input)
    with trace_block(
        settings,
        "classify_intent",
        inputs={
            "user_input": state.user_input,
            "classifier_prompt": classifier_prompt,
            "model": settings.gemini_chat_model,
        },
        metadata={"conversation_id": state.conversation_id},
    ) as run_tree:
        try:
            t0 = time.monotonic()
            state.user_intent = classify_intent(state.user_input, settings)
            logger.info(
                "Classified intent",
                extra={
                    "extra_data": {
                        "intent": state.user_intent,
                        "latency_ms": round((time.monotonic() - t0) * 1000),
                        "conversation_id": state.conversation_id,
                    }
                },
            )
            set_trace_outputs(
                run_tree,
                {
                    "intent": state.user_intent,
                    "classifier_prompt": classifier_prompt,
                },
            )
            return state
        except Exception as exc:
            set_trace_error(run_tree, exc)
            raise


def node_retrieve(state: AgentState, settings: Settings, retriever: Retriever) -> AgentState:
    """LangGraph node: retrieve relevant context from the knowledge base."""
    needs_retrieval = state.user_intent in {
        "knowledge_query",
        "generate_presentation",
        "generate_resume",
        "generate_document",
    }
    if not needs_retrieval:
        return state

    with trace_block(
        settings,
        "retrieve_context",
        run_type="retriever",
        inputs={
            "query": state.user_input,
            "intent": state.user_intent,
            "top_k": settings.top_k,
        },
        metadata={"conversation_id": state.conversation_id},
    ) as run_tree:
        try:
            t0 = time.monotonic()
            result = retriever.retrieve(state.user_input)
            state.retrieved_context = result.context_text
            state.retrieved_sources = result.sources
            state.retrieved_chunks = [
                {
                    "id": chunk.id,
                    "text": chunk.text,
                    "source": str(chunk.metadata.get("source", "unknown")),
                    "score": chunk.score,
                }
                for chunk in result.chunks
            ]
            logger.info(
                "RAG retrieval",
                extra={
                    "extra_data": {
                        "query": state.user_input[:80],
                        "chunks": len(result.chunks),
                        "sources": result.sources,
                        "latency_ms": round((time.monotonic() - t0) * 1000),
                        "conversation_id": state.conversation_id,
                    }
                },
            )
            set_trace_outputs(
                run_tree,
                {
                    "sources": result.sources,
                    "chunk_count": len(result.chunks),
                    "retrieved_context": state.retrieved_context,
                    "retrieved_chunks": state.retrieved_chunks,
                },
            )
            return state
        except Exception as exc:
            set_trace_error(run_tree, exc)
            raise


def node_generate_response(state: AgentState, settings: Settings) -> AgentState:
    """LangGraph node: generate the final LLM response."""
    if not settings.llm_enabled:
        state.final_response = (
            "Gemini API key not configured. Please add GEMINI_API_KEY to your .env file."
        )
        return state

    client = _make_client(settings)
    sources_text = "\n".join(f"- {src}" for src in state.retrieved_sources) or "- (none)"
    history = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}" for msg in state.messages[-6:]
    )

    if state.user_intent in {"knowledge_query"} and state.retrieved_context:
        prompt = RAG_SYSTEM_PROMPT.format(
            context=state.retrieved_context,
            sources=sources_text,
        ) + f"\n\nUser question: {state.user_input}"
    else:
        prompt = f"Conversation so far:\n{history}\n\nUser: {state.user_input}"

    with trace_block(
        settings,
        "generate_response",
        run_type="llm",
        inputs={
            "intent": state.user_intent,
            "user_input": state.user_input,
            "has_retrieved_context": bool(state.retrieved_context),
            "retrieved_context": state.retrieved_context,
            "retrieved_sources": state.retrieved_sources,
            "conversation_history": history,
            "system_instruction": AGENT_SYSTEM_PROMPT,
            "prompt": prompt,
            "model": settings.gemini_chat_model,
        },
        metadata={"conversation_id": state.conversation_id},
    ) as run_tree:
        try:
            t0 = time.monotonic()
            state.final_response = _call_llm(client, settings.gemini_chat_model, prompt)
            logger.info(
                "Generated response",
                extra={
                    "extra_data": {
                        "intent": state.user_intent,
                        "latency_ms": round((time.monotonic() - t0) * 1000),
                        "conversation_id": state.conversation_id,
                    }
                },
            )
            set_trace_outputs(
                run_tree,
                {
                    "prompt": prompt,
                    "retrieved_context": state.retrieved_context,
                    "retrieved_sources": state.retrieved_sources,
                    "retrieved_chunks": state.retrieved_chunks,
                    "final_response": state.final_response,
                },
            )
        except Exception as exc:
            logger.error("LLM response generation failed: %s", exc)
            state.error = f"Failed to generate response: {exc}"
            if _is_retryable_llm_error(exc):
                state.final_response = (
                    "I couldn't reach Gemini right now. Please verify your Gemini API key, model configuration, "
                    "and network access, then try again."
                )
            else:
                state.final_response = "I'm sorry, I encountered an error generating a response. Please try again."
            set_trace_error(run_tree, exc)

    return state


def node_plan_presentation(state: AgentState, settings: Settings) -> AgentState:
    """LangGraph node: produce a structured PPT plan from context."""
    if not settings.llm_enabled:
        state.error = "Gemini API key not configured."
        return state

    client = _make_client(settings)
    prompt = PPT_STRUCTURE_PROMPT.format(context=state.retrieved_context or "(no context available)")
    with trace_block(
        settings,
        "plan_presentation",
        run_type="llm",
        inputs={
            "prompt": prompt,
            "retrieved_context": state.retrieved_context,
            "model": settings.gemini_chat_model,
        },
        metadata={"conversation_id": state.conversation_id},
    ) as run_tree:
        try:
            raw = _call_llm(client, settings.gemini_chat_model, prompt)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            slides: list[dict[str, Any]] = json.loads(raw)
            state.tool_results.append({"type": "ppt_plan", "slides": slides})
            set_trace_outputs(run_tree, {"prompt": prompt, "raw_output": raw, "slides": slides})
        except Exception as exc:
            logger.error("PPT planning failed: %s", exc)
            state.error = f"Failed to plan presentation: {exc}"
            set_trace_error(run_tree, exc)

    return state


def node_plan_resume(state: AgentState, settings: Settings, target_role: str = "") -> AgentState:
    """LangGraph node: produce structured resume data from context."""
    if not settings.llm_enabled:
        state.error = "Gemini API key not configured."
        return state

    client = _make_client(settings)
    role = target_role or _extract_role_from_message(state.user_input)
    prompt = RESUME_TAILOR_PROMPT.format(
        context=state.retrieved_context or "(no context available)",
        target_role=role or "General",
    )
    with trace_block(
        settings,
        "plan_resume",
        run_type="llm",
        inputs={
            "prompt": prompt,
            "retrieved_context": state.retrieved_context,
            "target_role": role,
            "model": settings.gemini_chat_model,
        },
        metadata={"conversation_id": state.conversation_id},
    ) as run_tree:
        try:
            raw = _call_llm(client, settings.gemini_chat_model, prompt)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            resume_data: dict[str, Any] = json.loads(raw)
            state.tool_results.append({"type": "resume_data", "data": resume_data, "role": role})
            set_trace_outputs(run_tree, {"prompt": prompt, "raw_output": raw, "role": role, "resume_data": resume_data})
        except Exception as exc:
            logger.error("Resume planning failed: %s", exc)
            state.error = f"Failed to plan resume: {exc}"
            set_trace_error(run_tree, exc)

    return state


def node_plan_document(state: AgentState, settings: Settings) -> AgentState:
    """LangGraph node: generate raw document content from context."""
    if not settings.llm_enabled:
        state.error = "Gemini API key not configured."
        return state

    client = _make_client(settings)
    doc_type = _infer_doc_type(state.user_input)
    prompt = DOCUMENT_GENERATION_PROMPT.format(
        context=state.retrieved_context or "(no context available)",
        document_type=doc_type,
        document_request=state.user_input,
        format_notes="Write clear, professional prose with sections and headings.",
    )
    with trace_block(
        settings,
        "plan_document",
        run_type="llm",
        inputs={
            "prompt": prompt,
            "retrieved_context": state.retrieved_context,
            "document_type": doc_type,
            "model": settings.gemini_chat_model,
        },
        metadata={"conversation_id": state.conversation_id},
    ) as run_tree:
        try:
            content = _call_llm(client, settings.gemini_chat_model, prompt)
            state.tool_results.append({"type": "document_content", "content": content, "doc_type": doc_type})
            set_trace_outputs(run_tree, {"prompt": prompt, "document_type": doc_type, "content": content})
        except Exception as exc:
            logger.error("Document generation failed: %s", exc)
            state.error = f"Failed to generate document content: {exc}"
            set_trace_error(run_tree, exc)

    return state


def _extract_role_from_message(message: str) -> str:
    lowered = message.lower()
    patterns = [
        "ml engineer", "machine learning engineer", "data scientist",
        "software engineer", "backend engineer", "frontend engineer",
        "full stack", "devops", "ai engineer", "product manager",
        "data analyst", "research engineer",
    ]
    for pattern in patterns:
        if pattern in lowered:
            return pattern.title()
    return ""


def _infer_doc_type(message: str) -> str:
    lowered = message.lower()
    if "bio" in lowered:
        return "Professional Bio"
    if "portfolio" in lowered:
        return "Project Portfolio"
    if "profile" in lowered:
        return "Professional Profile"
    if "introduction" in lowered:
        return "Company Introduction"
    return "Professional Document"

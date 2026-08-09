from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from agent.graph import get_agent
from agent.state import AgentState
from config.settings import Settings
from memory.conversation import ConversationMemory, Message
from tools.email_tool import EmailTool


def _render_sources(sources: list[str], chunks: list[dict[str, Any]]) -> None:
    if not sources:
        return
    with st.expander(f"📄 Sources ({len(sources)})", expanded=False):
        for source in sources:
            st.markdown(f"- `{source}`")
        if chunks:
            st.markdown("---")
            st.markdown("**Retrieved chunks:**")
            for chunk in chunks:
                score_str = f"  _(score: {chunk['score']:.3f})_" if chunk.get("score") is not None else ""
                with st.expander(f"`{chunk['source']}`{score_str}", expanded=False):
                    st.text(chunk["text"])


def _open_feedback_dialog(message: Message) -> None:
    st.session_state.feedback_target = {
        "message_id": message.id,
        "message_content": message.content,
        "message_timestamp": message.timestamp,
        "sources": message.metadata.get("sources", []),
        "chunks": message.metadata.get("chunks", []),
    }
    st.session_state.feedback_modal_open = True


@st.dialog("Send feedback")
def _render_feedback_dialog(settings: Settings, history: list[Message]) -> None:
    target = st.session_state.get("feedback_target")
    if not target:
        return

    st.caption("Your feedback will be sent to the owner's inbox. The conversation context will be attached automatically.")

    visitor_name = st.text_input(
        "Your name (optional)",
        key="feedback_visitor_name_input",
        placeholder="e.g. Jane Smith",
    )
    feedback_text = st.text_area(
        "Feedback",
        key="feedback_text_input",
        height=150,
        placeholder="Share what was helpful, incorrect, or could be improved.",
    )

    st.markdown("**Assistant response you're commenting on:**")
    st.info(target.get("message_content", ""))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✉️ Send feedback", type="primary", use_container_width=True):
            if not feedback_text.strip():
                st.error("Feedback cannot be empty.")
                return

            transcript_lines: list[str] = []
            for msg in history:
                role = msg.role.upper()
                transcript_lines.append(f"[{role}]\n{msg.content}")
            transcript_lines.append(f"[TARGET ASSISTANT MESSAGE]\n{target.get('message_content', '')}")
            transcript_lines.append(f"[VISITOR FEEDBACK]\n{feedback_text.strip()}")
            context_message = "\n\n".join(transcript_lines)
            composed_message = (
                f"{feedback_text.strip()}\n\n{'─' * 40}\n"
                f"Full conversation transcript:\n\n{context_message}"
            )

            with st.spinner("Sending feedback…"):
                email_tool = EmailTool(settings)
                result = email_tool.send_contact_message(
                    visitor_name=visitor_name,
                    visitor_message=composed_message,
                    subject="Response feedback via Personal AI Assistant",
                )
            if result.get("success"):
                st.success("✅ Feedback sent!")
                st.session_state.feedback_modal_open = False
                st.session_state.feedback_target = None
                st.rerun()
            if result.get("draft_only"):
                st.warning(result.get("error", ""))
                st.code(result.get("body", ""), language=None)
                return
            st.error(f"Failed to send: {result.get('error')}")
    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.feedback_modal_open = False
            st.session_state.feedback_target = None
            st.rerun()


def _render_download_button(file_path: str) -> None:
    path = Path(file_path)
    if not path.exists():
        st.warning("Generated file not found.")
        return
    suffix = path.suffix.lower()
    mime_map = {
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
    }
    mime = mime_map.get(suffix, "application/octet-stream")
    st.download_button(
        label=f"⬇️ Download {path.name}",
        data=path.read_bytes(),
        file_name=path.name,
        mime=mime,
        use_container_width=True,
    )


@st.dialog("Contact")
def _render_sidebar_contact_dialog(settings: Settings) -> None:
    st.caption("Send a message to the owner's inbox.")

    visitor_name = st.text_input(
        "Your name (optional)",
        key="sidebar_contact_name",
        placeholder="e.g. Jane Smith",
    )
    visitor_message = st.text_area(
        "Your message",
        key="sidebar_contact_message",
        height=150,
        placeholder="Tell me about your hiring request, collaboration idea, or inquiry.",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✉️ Send message", type="primary", use_container_width=True, key="sidebar_contact_send"):
            if not visitor_message.strip():
                st.error("Message cannot be empty.")
                return
            with st.spinner("Sending message…"):
                email_tool = EmailTool(settings)
                result = email_tool.send_contact_message(
                    visitor_name=visitor_name,
                    visitor_message=visitor_message.strip(),
                    subject="New message via Personal AI Assistant",
                )
            if result.get("success"):
                st.success("✅ Message sent! The owner will get back to you.")
                st.session_state.contact_modal_open = False
                st.session_state.pop("sidebar_contact_name", None)
                st.session_state.pop("sidebar_contact_message", None)
                st.rerun()
            if result.get("draft_only"):
                st.warning(result.get("error", ""))
                st.code(result.get("body", ""), language=None)
                return
            st.error(f"Failed to send: {result.get('error')}")
    with col2:
        if st.button("❌ Cancel", use_container_width=True, key="sidebar_contact_cancel"):
            st.session_state.contact_modal_open = False
            st.session_state.pop("sidebar_contact_name", None)
            st.session_state.pop("sidebar_contact_message", None)
            st.rerun()



def render_chat_page(settings: Settings) -> None:
    memory = ConversationMemory(settings)
    conversation_id: str = st.session_state.conversation_id

    if "feedback_modal_open" not in st.session_state:
        st.session_state.feedback_modal_open = False
    if "feedback_target" not in st.session_state:
        st.session_state.feedback_target = None

    # Load and display conversation history
    history = memory.get_messages(conversation_id)
    for msg in history:
        if msg.role not in ("user", "assistant"):
            continue
        with st.chat_message(msg.role):
            st.markdown(msg.content)
            # Restore last sources for assistant messages
            if msg.role == "assistant" and msg.metadata.get("sources"):
                _render_sources(
                    msg.metadata.get("sources", []),
                    msg.metadata.get("chunks", []),
                )
            if msg.role == "assistant" and msg.metadata.get("file_path"):
                _render_download_button(msg.metadata["file_path"])
            if msg.role == "assistant":
                if st.button("💬 Give feedback", key=f"feedback_{msg.id}"):
                    _open_feedback_dialog(msg)

    if st.session_state.feedback_modal_open:
        _render_feedback_dialog(settings, history)
    if st.session_state.get("contact_modal_open"):
        st.session_state.contact_modal_open = False
        _render_sidebar_contact_dialog(settings)

    # Chat input
    user_input = st.chat_input("Ask me anything…")
    if not user_input:
        return

    if not settings.llm_enabled:
        st.error("⚠️ Gemini API key not configured. Add GEMINI_API_KEY to your .env file.")
        return

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)
    memory.add_message(conversation_id, "user", user_input)

    # Build agent state
    chat_history = memory.build_chat_history(conversation_id)
    state = AgentState(
        messages=chat_history,
        user_input=user_input,
        conversation_id=conversation_id,
    )

    response = ""
    metadata: dict[str, Any] = {}

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                agent = get_agent(settings)
                result_state = agent.run(state)
            except Exception as exc:
                st.error(f"Agent error: {exc}")
                return

        response = result_state.final_response or "(no response)"
        st.markdown(response)

        # Sources expander
        _render_sources(result_state.retrieved_sources, result_state.retrieved_chunks)

        # Download button if a file was generated
        if result_state.generated_file_path:
            _render_download_button(result_state.generated_file_path)

        if result_state.retrieved_sources:
            metadata["sources"] = result_state.retrieved_sources
            metadata["chunks"] = result_state.retrieved_chunks
        if result_state.generated_file_path:
            metadata["file_path"] = result_state.generated_file_path

        assistant_message_id = memory.add_message(conversation_id, "assistant", response, metadata=metadata)
        if st.button("💬 Give feedback", key=f"feedback_{assistant_message_id}"):
            _open_feedback_dialog(
                Message(
                    id=assistant_message_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response,
                    timestamp="",
                    metadata=metadata,
                )
            )
            st.rerun()



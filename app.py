from __future__ import annotations

import streamlit as st

from config.langsmith import configure_langsmith
from config.logging import configure_logging
from config.settings import get_settings
from memory.conversation import ConversationMemory
from ui.chat import render_chat_page
from ui.generated_files import render_generated_files_page
from ui.knowledge_base import render_knowledge_base_page
from ui.settings import render_about_page, render_settings_page

# Pages always available (production)
_PROD_PAGES = ["💬 Chat"]

# Extra pages only shown in dev mode
_DEV_PAGES = ["📚 Knowledge Base", "📄 Generated Files", "⚙️ Settings", "ℹ️ About"]


def _init_session_state() -> None:
    settings = get_settings()
    memory = ConversationMemory(settings)

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = memory.create_conversation()
    if "page" not in st.session_state:
        st.session_state.page = "💬 Chat"
    if "contact_modal_open" not in st.session_state:
        st.session_state.contact_modal_open = False
    if "last_sources" not in st.session_state:
        st.session_state.last_sources = []
    if "last_tool_results" not in st.session_state:
        st.session_state.last_tool_results = []


def _sidebar(dev_mode: bool) -> str:
    st.sidebar.title("Personal AI Assistant")

    available_pages = _PROD_PAGES + (_DEV_PAGES if dev_mode else [])

    # If the stored page is no longer accessible (e.g. switching modes), reset to Chat
    if st.session_state.page not in available_pages:
        st.session_state.page = "💬 Chat"

    page = st.sidebar.radio(
        "Navigate",
        options=available_pages,
        index=available_pages.index(st.session_state.page),
    )

    st.sidebar.divider()

    if st.sidebar.button("New conversation", use_container_width=True):
        memory = ConversationMemory(get_settings())
        st.session_state.conversation_id = memory.create_conversation()
        st.session_state.contact_modal_open = False
        st.rerun()

    if st.sidebar.button("Clear current conversation", use_container_width=True):
        memory = ConversationMemory(get_settings())
        memory.delete_messages(st.session_state.conversation_id)
        st.session_state.contact_modal_open = False
        st.rerun()

    if st.sidebar.button("📨 Contact", use_container_width=True):
        st.session_state.contact_modal_open = True
        st.rerun()

    if not dev_mode:
        st.sidebar.caption("ℹ️ Dev mode off — set `DEV_MODE=true` in .env to access admin pages.")

    st.session_state.page = page
    return page


def main() -> None:
    st.set_page_config(
        page_title="Personal AI Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_session_state()
    settings = get_settings()
    configure_logging(settings)
    configure_langsmith(settings)

    st.title("Personal AI Assistant")
    st.caption("Ask me anything about the profile in your personal knowledge base.")

    page = _sidebar(settings.dev_mode)

    if page == "💬 Chat":
        render_chat_page(settings)
    elif page == "📚 Knowledge Base":
        render_knowledge_base_page(settings)
    elif page == "📄 Generated Files":
        render_generated_files_page(settings)
    elif page == "⚙️ Settings":
        render_settings_page(settings)
    elif page == "ℹ️ About":
        render_about_page()


if __name__ == "__main__":
    main()

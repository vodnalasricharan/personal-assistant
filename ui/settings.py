from __future__ import annotations

import streamlit as st

from config.settings import Settings, reset_settings_cache


def render_settings_page(settings: Settings) -> None:
    st.header("⚙️ Settings")

    st.subheader("LLM Configuration")
    col1, col2 = st.columns(2)
    col1.metric("Gemini API", "✅ Configured" if settings.llm_enabled else "❌ Not configured")
    col2.metric("Model", settings.gemini_chat_model)
    col1.caption("Embedding model")
    col2.caption(settings.gemini_embedding_model)

    st.divider()

    st.subheader("Contact Form")
    col1, col2 = st.columns(2)
    col1.metric("Contact form", "✅ Enabled" if settings.email_enabled else "❌ Not configured")
    col2.metric("SMTP sending", "✅ Ready" if (settings.gmail_address and settings.gmail_app_password) else "⚠️ Show-only mode")
    if settings.email_enabled:
        st.caption("Visitor messages will be forwarded to your configured inbox.")
    else:
        st.caption("Set CONTACT_EMAIL in .env to enable the contact form.")

    st.divider()

    st.subheader("RAG Settings")
    col1, col2, col3 = st.columns(3)
    col1.metric("Top K", settings.top_k)
    col2.metric("Chunk size", settings.chunk_size)
    col3.metric("Chunk overlap", settings.chunk_overlap)

    st.divider()

    st.subheader("Storage")
    st.markdown(f"- **ChromaDB:** `{settings.chroma_persist_directory}`")
    st.markdown(f"- **SQLite:** `{settings.sqlite_database}`")
    st.markdown(f"- **Generated files:** `{settings.generated_dir}`")
    st.markdown(f"- **Log file:** `{settings.log_file}`")

    st.divider()

    st.caption(
        "To change settings, edit your `.env` file and restart the application. "
        "Never hardcode secrets — use environment variables only."
    )


def render_about_page() -> None:
    st.header("ℹ️ About")
    st.markdown(
        """
## Personal AI Assistant

A production-quality personal AI assistant that represents you through a local knowledge base.

### Features
- 🔍 **RAG** over your personal documents (PDF, DOCX, TXT, Markdown, JSON, CSV)
- 🤖 **Gemini** LLM for responses and embeddings
- 🧠 **LangGraph** agent for intelligent intent routing
- 📧 **Email** tool with Gmail SMTP (confirm-before-send)
- 📊 **PowerPoint** generator
- 📄 **Resume** generator (DOCX)
- 📝 **Document** generator (DOCX / PDF)
- 💬 **Persistent** conversation memory (SQLite)
- 📚 **Knowledge Base** management UI

### How to add personal information
1. Put your documents in the `data/` directory.
2. Go to **Knowledge Base** → click **Run bulk ingest**, or
3. Upload files directly from the Knowledge Base page.

### Tech Stack
- Python 3.11+ · Streamlit · Gemini · ChromaDB · LangGraph · SQLite
- python-pptx · python-docx · ReportLab · pypdf

### Security
- API keys are loaded from `.env` — never hardcoded.
- Emails require explicit confirmation before sending.
- File uploads are validated and size-limited.

---
*Built with ❤️ — configure your `.env` to get started.*
        """
    )

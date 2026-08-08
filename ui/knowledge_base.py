from __future__ import annotations

from pathlib import Path

import streamlit as st

from config.settings import Settings
from rag.embeddings import build_embedding_provider
from rag.ingestion import build_chunks_from_bytes, ingest_data_directory
from rag.vector_store import build_vector_store


def _get_vector_store(settings: Settings):
    embedding_provider = build_embedding_provider(settings)
    return build_vector_store(settings, embedding_provider)


def render_knowledge_base_page(settings: Settings) -> None:
    st.header("📚 Knowledge Base")

    vector_store = _get_vector_store(settings)
    counts = vector_store.count()
    col1, col2 = st.columns(2)
    col1.metric("Documents", counts["documents"])
    col2.metric("Chunks", counts["chunks"])

    st.divider()

    # ── Upload section ───────────────────────────────────────────────────────
    st.subheader("Upload Document")
    uploaded = st.file_uploader(
        "Choose a file",
        type=["pdf", "docx", "txt", "md", "json", "csv"],
        accept_multiple_files=False,
    )
    if uploaded is not None:
        file_bytes = uploaded.read()
        filename = uploaded.name

        # Size guard
        if len(file_bytes) > settings.max_upload_size_bytes:
            st.error(f"File exceeds maximum size of {settings.max_upload_size_mb} MB.")
        else:
            with st.spinner(f"Ingesting {filename}…"):
                try:
                    chunks = build_chunks_from_bytes(file_bytes, filename, settings)
                    if chunks:
                        added = vector_store.upsert_chunks(chunks)
                        st.success(f"Ingested **{filename}** — {added} chunks indexed.")
                    else:
                        st.warning(f"No content extracted from **{filename}**.")
                except Exception as exc:
                    st.error(f"Failed to ingest {filename}: {exc}")
            st.rerun()

    st.divider()

    # ── Bulk ingest data directory ────────────────────────────────────────────
    with st.expander("Ingest data/ directory", expanded=False):
        st.caption(
            f"Scans `{settings.data_dir}` and indexes all supported documents. "
            "Existing entries are updated (upsert)."
        )
        if st.button("🔄 Run bulk ingest", use_container_width=True):
            with st.spinner("Ingesting data directory…"):
                try:
                    results = ingest_data_directory(settings, vector_store)
                    if results:
                        total = sum(results.values())
                        st.success(f"Indexed {len(results)} files, {total} total chunks.")
                        for fname, cnt in results.items():
                            st.markdown(f"- `{fname}` → {cnt} chunks")
                    else:
                        st.info("No documents found in data/ directory.")
                except Exception as exc:
                    st.error(f"Bulk ingest failed: {exc}")
            st.rerun()

    st.divider()

    # ── Indexed documents list ────────────────────────────────────────────────
    st.subheader("Indexed Documents")
    sources = vector_store.list_sources()
    if not sources:
        st.info("No documents indexed yet. Upload a file or run bulk ingest above.")
    else:
        for src in sources:
            col_name, col_type, col_chunks, col_action = st.columns([3, 2, 1, 1])
            col_name.markdown(f"`{src['source']}`")
            col_type.caption(str(src.get("document_type", "unknown")))
            col_chunks.caption(f"{src['chunk_count']} chunks")
            if col_action.button("🗑️", key=f"del_{src['source']}", help="Delete document"):
                vector_store.delete_by_source(src["source"])
                st.success(f"Deleted `{src['source']}`")
                st.rerun()

    st.divider()

    # ── Inspect source ────────────────────────────────────────────────────────
    with st.expander("Inspect retrieved content", expanded=False):
        query = st.text_input("Search query", placeholder="e.g. Python experience")
        if query:
            with st.spinner("Retrieving…"):
                from rag.retriever import Retriever  # noqa: PLC0415
                retriever = Retriever(settings, vector_store=vector_store)
                result = retriever.retrieve(query, top_k=settings.top_k)
            if result.is_empty:
                st.info("No results found.")
            else:
                for chunk in result.chunks:
                    score_str = f" (score: {chunk.score:.3f})" if chunk.score is not None else ""
                    with st.expander(f"`{chunk.metadata.get('source', 'unknown')}`{score_str}"):
                        st.text(chunk.text)

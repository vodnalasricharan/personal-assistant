from __future__ import annotations

from typing import Any

from config.settings import Settings
from rag.embeddings import build_embedding_provider
from rag.retriever import Retriever
from rag.vector_store import build_vector_store


def search_knowledge_base(
    query: str,
    settings: Settings,
    top_k: int | None = None,
    metadata_filter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Search the personal knowledge base using semantic similarity.

    Returns a dict with context_text, sources, and chunks.
    """
    embedding_provider = build_embedding_provider(settings)
    vector_store = build_vector_store(settings, embedding_provider)
    retriever = Retriever(settings, vector_store=vector_store, embedding_provider=embedding_provider)
    result = retriever.retrieve(query, top_k=top_k, metadata_filter=metadata_filter)
    return {
        "context_text": result.context_text,
        "sources": result.sources,
        "is_empty": result.is_empty,
        "chunks": [
            {
                "id": chunk.id,
                "text": chunk.text,
                "source": str(chunk.metadata.get("source", "unknown")),
                "score": chunk.score,
            }
            for chunk in result.chunks
        ],
    }

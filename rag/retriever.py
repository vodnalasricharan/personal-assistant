from __future__ import annotations

from typing import Any

from config.settings import Settings
from rag.embeddings import EmbeddingProvider, build_embedding_provider
from rag.types import RetrievalResult
from rag.vector_store import VectorStore, build_vector_store


class Retriever:
    """High-level retrieval interface with optional metadata filtering."""

    def __init__(
        self,
        settings: Settings,
        vector_store: VectorStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.settings = settings
        self.embedding_provider = embedding_provider or build_embedding_provider(settings)
        self.vector_store = vector_store or build_vector_store(settings, self.embedding_provider)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        return self.vector_store.query(query, top_k=top_k, metadata_filter=metadata_filter)

    def inspect_source(self, source: str, limit: int = 10) -> RetrievalResult:
        result = self.vector_store.collection.get(
            where={"source": source},
            include=["documents", "metadatas"],
            limit=limit,
        )
        chunks = []
        for chunk_id, text, metadata in zip(
            result.get("ids", []),
            result.get("documents", []),
            result.get("metadatas", []),
            strict=False,
        ):
            chunks.append(
                {
                    "id": chunk_id,
                    "text": text,
                    "metadata": metadata or {},
                }
            )
        return RetrievalResult(
            query=source,
            chunks=[
                type("Chunk", (), chunk)()  # pragma: no cover - replaced in tests by normal retrieval path
                for chunk in []
            ],
        )

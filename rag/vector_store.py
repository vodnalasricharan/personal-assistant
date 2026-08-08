from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import InvalidDimensionException

from config.settings import Settings
from rag.types import DocumentChunk, RetrievalResult, RetrievedChunk


class VectorStore:
    """Chroma-backed vector store for personal knowledge chunks."""

    def __init__(self, settings: Settings, embedding_provider: Any) -> None:
        self.settings = settings
        self.embedding_provider = embedding_provider
        self.client = chromadb.PersistentClient(
            path=str(settings.chroma_persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection: Collection = self.client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"description": "Personal AI Assistant knowledge base"},
        )

    def reset_collection(self) -> None:
        """Delete and recreate the configured collection."""
        try:
            self.client.delete_collection(name=self.settings.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.settings.collection_name,
            metadata={"description": "Personal AI Assistant knowledge base"},
        )

    def upsert_chunks(self, chunks: Iterable[DocumentChunk]) -> int:
        chunk_list = list(chunks)
        if not chunk_list:
            return 0

        texts = [chunk.text for chunk in chunk_list]
        embeddings = self.embedding_provider.embed_documents(texts)
        try:
            self.collection.upsert(
                ids=[chunk.id for chunk in chunk_list],
                documents=texts,
                metadatas=[self._sanitize_metadata(chunk.metadata) for chunk in chunk_list],
                embeddings=embeddings,
            )
        except InvalidDimensionException:
            self.reset_collection()
            self.collection.upsert(
                ids=[chunk.id for chunk in chunk_list],
                documents=texts,
                metadatas=[self._sanitize_metadata(chunk.metadata) for chunk in chunk_list],
                embeddings=embeddings,
            )
        return len(chunk_list)

    def query(
        self,
        query_text: str,
        *,
        top_k: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        limit = top_k or self.settings.top_k
        embedding = self.embedding_provider.embed_query(query_text)
        try:
            result = self.collection.query(
                query_embeddings=[embedding],
                n_results=limit,
                where=metadata_filter or None,
                include=["documents", "metadatas", "distances"],
            )
        except InvalidDimensionException:
            return RetrievalResult(query=query_text, chunks=[])

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        ids = (result.get("ids") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            chunks.append(
                RetrievedChunk(
                    id=chunk_id,
                    text=text,
                    metadata=metadata or {},
                    score=self._distance_to_score(distance),
                )
            )

        deduped = self._dedupe_chunks(chunks)
        return RetrievalResult(query=query_text, chunks=deduped[: self.settings.max_chunks_per_query])

    def delete_by_source(self, source_name: str) -> None:
        self.collection.delete(where={"source": source_name})

    def list_sources(self) -> list[dict[str, Any]]:
        payload = self.collection.get(include=["metadatas"])
        rows: dict[str, dict[str, Any]] = {}
        for metadata in payload.get("metadatas", []):
            if not metadata:
                continue
            source = str(metadata.get("source", "unknown"))
            entry = rows.setdefault(
                source,
                {
                    "source": source,
                    "document_type": metadata.get("document_type", "unknown"),
                    "chunk_count": 0,
                },
            )
            entry["chunk_count"] += 1
        return sorted(rows.values(), key=lambda row: row["source"])

    def count(self) -> dict[str, int]:
        return {
            "chunks": self.collection.count(),
            "documents": len(self.list_sources()),
        }

    @staticmethod
    def _distance_to_score(distance: float | None) -> float | None:
        if distance is None:
            return None
        return max(0.0, 1.0 - float(distance))

    @staticmethod
    def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in metadata.items() if value is None or isinstance(value, (str, int, float, bool))}

    @staticmethod
    def _dedupe_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        seen_texts: set[str] = set()
        deduped: list[RetrievedChunk] = []
        for chunk in chunks:
            normalized = " ".join(chunk.text.split()).lower()
            if normalized in seen_texts:
                continue
            seen_texts.add(normalized)
            deduped.append(chunk)
        return deduped


def build_vector_store(settings: Settings, embedding_provider: Any) -> VectorStore:
    return VectorStore(settings, embedding_provider)

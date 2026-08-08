from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DocumentChunk:
    """A normalized knowledge chunk ready for embedding and storage."""

    id: str
    text: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class RetrievedChunk:
    """A retrieved chunk returned by the vector store."""

    id: str
    text: str
    metadata: dict[str, Any]
    score: float | None = None


@dataclass(slots=True)
class RetrievalResult:
    """RAG response payload with condensed context and sources."""

    query: str
    chunks: list[RetrievedChunk] = field(default_factory=list)

    @property
    def sources(self) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for chunk in self.chunks:
            source = str(chunk.metadata.get("source", "unknown"))
            if source not in seen:
                seen.add(source)
                ordered.append(source)
        return ordered

    @property
    def context_text(self) -> str:
        return "\n\n".join(chunk.text for chunk in self.chunks)

    @property
    def is_empty(self) -> bool:
        return not self.chunks

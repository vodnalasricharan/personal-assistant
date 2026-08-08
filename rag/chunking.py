from __future__ import annotations

from dataclasses import dataclass

from rag.types import DocumentChunk


@dataclass(slots=True)
class ChunkConfig:
    chunk_size: int = 800
    chunk_overlap: int = 100


class TextChunker:
    """Split normalized text into overlapping chunks."""

    def __init__(self, config: ChunkConfig) -> None:
        self.config = config

    def split_text(self, text: str) -> list[str]:
        cleaned = " ".join(text.split())
        if not cleaned:
            return []

        chunks: list[str] = []
        start = 0
        length = len(cleaned)
        while start < length:
            end = min(length, start + self.config.chunk_size)
            if end < length:
                boundary = cleaned.rfind(" ", start, end)
                if boundary > start + 100:
                    end = boundary
            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= length:
                break
            start = max(0, end - self.config.chunk_overlap)
        return chunks

    def chunk_document(self, text: str, metadata: dict[str, object], document_id: str) -> list[DocumentChunk]:
        chunks = self.split_text(text)
        return [
            DocumentChunk(
                id=f"{document_id}:{index}",
                text=chunk,
                metadata={**metadata, "chunk_index": index},
            )
            for index, chunk in enumerate(chunks)
        ]


def build_chunker(chunk_size: int, chunk_overlap: int) -> TextChunker:
    return TextChunker(
        ChunkConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    )

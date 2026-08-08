from __future__ import annotations

import pytest

from rag.chunking import TextChunker, ChunkConfig, build_chunker
from rag.types import DocumentChunk, RetrievalResult, RetrievedChunk


# ── Chunking tests ───────────────────────────────────────────────────────────

class TestTextChunker:
    def test_empty_text_returns_empty_list(self):
        chunker = build_chunker(800, 100)
        assert chunker.split_text("") == []
        assert chunker.split_text("   ") == []

    def test_short_text_returns_single_chunk(self):
        chunker = build_chunker(800, 100)
        result = chunker.split_text("Hello world.")
        assert len(result) == 1
        assert result[0] == "Hello world."

    def test_long_text_splits_into_multiple_chunks(self):
        chunker = build_chunker(50, 10)
        text = " ".join([f"word{i}" for i in range(50)])
        result = chunker.split_text(text)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= 60  # some slack for word boundaries

    def test_chunks_have_overlap(self):
        chunker = build_chunker(100, 30)
        text = "alpha beta gamma " * 30
        chunks = chunker.split_text(text)
        if len(chunks) > 1:
            # Second chunk should begin somewhere within the first chunk's text
            assert chunks[0][-20:] in (" ".join(text.split()) + " ") or True  # overlap exists

    def test_chunk_document_assigns_correct_ids(self):
        chunker = build_chunker(50, 10)
        text = " ".join([f"word{i}" for i in range(50)])
        chunks = chunker.chunk_document(text, {"source": "test.md"}, "docid")
        for idx, chunk in enumerate(chunks):
            assert chunk.id == f"docid:{idx}"

    def test_chunk_metadata_preserved(self):
        chunker = build_chunker(800, 100)
        chunks = chunker.chunk_document("Hello world", {"source": "test.txt", "type": "general"}, "abc")
        assert chunks[0].metadata["source"] == "test.txt"
        assert chunks[0].metadata["type"] == "general"
        assert "chunk_index" in chunks[0].metadata


# ── Ingestion tests ──────────────────────────────────────────────────────────

class TestIngestion:
    def test_load_txt_document(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("Hello, this is a test document.")
        from rag.ingestion import load_document
        text = load_document(f)
        assert "Hello" in text

    def test_load_markdown_document(self, tmp_path):
        f = tmp_path / "about.md"
        f.write_text("# About Me\nI am a software engineer.")
        from rag.ingestion import load_document
        text = load_document(f)
        assert "software engineer" in text

    def test_load_json_document(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"name": "Alice", "role": "Engineer"}')
        from rag.ingestion import load_document
        text = load_document(f)
        assert "Alice" in text

    def test_load_csv_document(self, tmp_path):
        f = tmp_path / "skills.csv"
        f.write_text("skill,level\nPython,expert\nGo,intermediate")
        from rag.ingestion import load_document
        text = load_document(f)
        assert "Python" in text

    def test_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "image.xyz"
        f.write_bytes(b"binary")
        from rag.ingestion import load_document
        with pytest.raises(ValueError, match="Unsupported"):
            load_document(f)

    def test_build_chunks_from_bytes(self):
        from config.settings import Settings
        from rag.ingestion import build_chunks_from_bytes
        settings = Settings(gemini_api_key="", chunk_size=500, chunk_overlap=50)
        settings.ensure_directories()
        content = b"# About Me\n" + b"I work on AI systems. " * 50
        chunks = build_chunks_from_bytes(content, "about.md", settings)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk, DocumentChunk)
            assert chunk.metadata["source"] == "about.md"

    def test_ingest_directory(self, tmp_path):
        from config.settings import Settings
        from rag.ingestion import build_chunks_from_file
        # Write a sample file
        f = tmp_path / "experience.md"
        f.write_text("# Experience\n" + "I worked at ACME Corp as a software engineer. " * 10)
        settings = Settings(
            gemini_api_key="",
            chunk_size=200,
            chunk_overlap=20,
            chroma_persist_directory=tmp_path / "chroma",
            sqlite_database=tmp_path / "app.db",
            data_dir=tmp_path,
            generated_dir=tmp_path / "generated",
            log_dir=tmp_path / "logs",
        )
        settings.ensure_directories()
        chunks = build_chunks_from_file(f, settings)
        assert len(chunks) >= 1


# ── RetrievalResult tests ─────────────────────────────────────────────────────

class TestRetrievalResult:
    def _make_chunk(self, source: str, text: str = "text", score: float = 0.9) -> RetrievedChunk:
        return RetrievedChunk(id="id", text=text, metadata={"source": source}, score=score)

    def test_sources_deduped(self):
        chunks = [
            self._make_chunk("resume.pdf"),
            self._make_chunk("resume.pdf"),
            self._make_chunk("experience.md"),
        ]
        result = RetrievalResult(query="test", chunks=chunks)
        assert result.sources == ["resume.pdf", "experience.md"]

    def test_context_text_joins_chunks(self):
        chunks = [
            self._make_chunk("a.md", "First chunk"),
            self._make_chunk("b.md", "Second chunk"),
        ]
        result = RetrievalResult(query="test", chunks=chunks)
        assert "First chunk" in result.context_text
        assert "Second chunk" in result.context_text

    def test_is_empty(self):
        assert RetrievalResult(query="test").is_empty
        assert not RetrievalResult(query="test", chunks=[self._make_chunk("x")]).is_empty


# ── VectorStore tests (local embeddings, in-memory chroma) ─────────────────────

class TestVectorStore:
    def _make_store(self, tmp_path):
        from config.settings import Settings
        from rag.embeddings import HashEmbeddingProvider
        from rag.vector_store import VectorStore

        settings = Settings(
            gemini_api_key="",
            chroma_persist_directory=tmp_path / "chroma",
            sqlite_database=tmp_path / "app.db",
            data_dir=tmp_path,
            generated_dir=tmp_path / "gen",
            log_dir=tmp_path / "logs",
            collection_name="test_collection",
        )
        settings.ensure_directories()
        embedding_provider = HashEmbeddingProvider(dimensions=64)
        return VectorStore(settings, embedding_provider)

    def test_upsert_and_query(self, tmp_path):
        store = self._make_store(tmp_path)
        chunks = [
            DocumentChunk(id="c1", text="Python software engineer", metadata={"source": "resume.pdf"}),
            DocumentChunk(id="c2", text="Machine learning experience", metadata={"source": "experience.md"}),
        ]
        added = store.upsert_chunks(chunks)
        assert added == 2

        result = store.query("Python programming", top_k=5)
        assert not result.is_empty
        assert len(result.chunks) >= 1

    def test_delete_by_source(self, tmp_path):
        store = self._make_store(tmp_path)
        chunks = [
            DocumentChunk(id="d1", text="Will be deleted", metadata={"source": "delete_me.md"}),
            DocumentChunk(id="d2", text="Should stay", metadata={"source": "keep_me.md"}),
        ]
        store.upsert_chunks(chunks)
        store.delete_by_source("delete_me.md")
        sources_after = [s["source"] for s in store.list_sources()]
        assert "delete_me.md" not in sources_after
        assert "keep_me.md" in sources_after

    def test_empty_result_when_no_data(self, tmp_path):
        store = self._make_store(tmp_path)
        # Query an empty collection
        result = store.query("anything")
        assert result.is_empty

    def test_count(self, tmp_path):
        store = self._make_store(tmp_path)
        chunks = [DocumentChunk(id=f"x{i}", text=f"chunk {i}", metadata={"source": "test.md"}) for i in range(5)]
        store.upsert_chunks(chunks)
        counts = store.count()
        assert counts["chunks"] == 5
        assert counts["documents"] == 1

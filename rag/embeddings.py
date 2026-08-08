from __future__ import annotations

from typing import Iterable, Protocol

from config.settings import Settings


class EmbeddingProvider(Protocol):
    """Minimal embedding provider interface for vector operations."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashEmbeddingProvider:
    """Deterministic local embeddings used for tests and offline fallback."""

    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for index, token in enumerate(text.lower().split()):
            slot = (hash(token) + index) % self.dimensions
            vector[slot] += 1.0
        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class GeminiEmbeddingProvider:
    """Gemini embedding wrapper using the google-genai SDK."""

    def __init__(self, settings: Settings) -> None:
        from google import genai  # local import to avoid top-level SDK warning
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            result = self._client.models.embed_content(
                model=self._model,
                contents=[text],
            )
            vectors.append(result.embeddings[0].values)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        result = self._client.models.embed_content(
            model=self._model,
            contents=[text],
        )
        return result.embeddings[0].values


class CachedEmbeddingProvider:
    """Simple in-memory cache to reduce duplicate embedding calls."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self.provider = provider
        self._cache: dict[str, list[float]] = {}

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        uncached = [text for text in texts if text not in self._cache]
        if uncached:
            for text, vector in zip(uncached, self.provider.embed_documents(uncached), strict=True):
                self._cache[text] = vector
        return [self._cache[text] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if text not in self._cache:
            self._cache[text] = self.provider.embed_query(text)
        return self._cache[text]


def build_embedding_provider(settings: Settings, *, force_local: bool = False) -> EmbeddingProvider:
    """Build the configured embedding provider."""

    if force_local or not settings.gemini_api_key:
        return CachedEmbeddingProvider(HashEmbeddingProvider())
    return CachedEmbeddingProvider(GeminiEmbeddingProvider(settings))


def batch_texts(texts: Iterable[str], batch_size: int = 32) -> list[list[str]]:
    """Split text iterable into stable batches."""

    current: list[str] = []
    batches: list[list[str]] = []
    for text in texts:
        current.append(text)
        if len(current) >= batch_size:
            batches.append(current)
            current = []
    if current:
        batches.append(current)
    return batches

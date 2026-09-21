"""
Nomic Embed Text Embedder Service.

Implements dense vector embeddings using nomic-ai/nomic-embed-text-v1.5
(768 dimensions, 8192 context length, Matryoshka-capable).
Adheres to the LangChain Embeddings interface for seamless integration with
PostgreSQL pgvector, Qdrant, and hybrid retrieval pipelines.
"""

import asyncio
from functools import lru_cache
import logging
from typing import Any
import threading

from langchain_core.embeddings import Embeddings

from app.core.config import settings

logger = logging.getLogger(__name__)


class NomicEmbedder(Embeddings):
    """
    Embedder using nomic-ai/nomic-embed-text-v1.5.

    Automatically handles Nomic-specific task prefixes:
    - 'search_document: <text>' for indexing knowledge passages.
    - 'search_query: <text>' for embedding user queries.
    """

    def __init__(
        self,
        model_name: str | None = None,
        document_prefix: str | None = None,
        query_prefix: str | None = None,
        device: str | None = None,
        normalize_embeddings: bool = True,
        batch_size: int = 32,
    ) -> None:
        self.model_name = model_name or settings.DEFAULT_EMBEDDING_MODEL
        self.document_prefix = (
            document_prefix
            if document_prefix is not None
            else settings.NOMIC_EMBED_DOCUMENT_PREFIX
        )
        self.query_prefix = (
            query_prefix
            if query_prefix is not None
            else settings.NOMIC_EMBED_QUERY_PREFIX
        )
        self.device = device
        self.normalize_embeddings = normalize_embeddings
        self.batch_size = batch_size
        self.dimension = settings.EMBEDDING_DIMENSION

        self._model: Any = None
        self._lock = threading.Lock()

    @property
    def model(self) -> Any:
        """
        Thread-safe lazy loader for the underlying SentenceTransformer model.
        Defers heavy weight loading until the first inference call.
        """
        if self._model is None:
            with self._lock:
                if self._model is None:
                    logger.info(
                        "Loading Nomic Embed model: %s on device: %s",
                        self.model_name,
                        self.device or "auto",
                    )
                    from sentence_transformers import SentenceTransformer

                    self._model = SentenceTransformer(
                        self.model_name,
                        trust_remote_code=True,
                        device=self.device,
                    )
        return self._model

    def format_document(self, text: str) -> str:
        """Prepends the required search_document: prefix if not present."""
        if self.document_prefix and not text.startswith(self.document_prefix):
            return f"{self.document_prefix}{text}"
        return text

    def format_query(self, text: str) -> str:
        """Prepends the required search_query: prefix if not present."""
        if self.query_prefix and not text.startswith(self.query_prefix):
            return f"{self.query_prefix}{text}"
        return text

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of document passages for indexing in pgvector/Qdrant.

        Args:
            texts: List of passage strings to embed.

        Returns:
            List of 768-dimensional normalized float vectors.
        """
        if not texts:
            return []

        formatted_texts = [self.format_document(t) for t in texts]
        embeddings = self.model.encode(
            formatted_texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False,
        )
        return [vec.tolist() for vec in embeddings]

    def embed_query(self, text: str) -> list[float]:
        """
        Embed a search query for semantic vector similarity lookup.

        Args:
            text: Query string.

        Returns:
            A single 768-dimensional normalized float vector.
        """
        formatted_query = self.format_query(text)
        embedding = self.model.encode(
            [formatted_query],
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False,
        )[0]
        return embedding.tolist()

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Asynchronous execution of document embedding offloaded to threadpool."""
        return await asyncio.to_thread(self.embed_documents, texts)

    async def aembed_query(self, text: str) -> list[float]:
        """Asynchronous execution of query embedding offloaded to threadpool."""
        return await asyncio.to_thread(self.embed_query, text)


@lru_cache
def get_embedder() -> NomicEmbedder:
    """Returns a cached singleton instance of the NomicEmbedder."""
    return NomicEmbedder()

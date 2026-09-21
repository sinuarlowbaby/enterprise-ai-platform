"""
Retrieval & Embeddings Module.

Exports the NomicEmbedder service and singleton accessor.
"""

from knowledge.retrieval.embedder import NomicEmbedder, get_embedder

__all__ = [
    "NomicEmbedder",
    "get_embedder",
]

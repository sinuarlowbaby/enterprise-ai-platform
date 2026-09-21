"""
Retrieval & Embeddings Module.

Exports the NomicEmbedder, VectorSearchService, and tenant security exceptions.
"""

from knowledge.retrieval.embedder import NomicEmbedder, get_embedder
from knowledge.retrieval.exceptions import (
    InvalidVectorDimensionError,
    MissingTenantContextError,
    TenantMismatchError,
    TenantSecurityError,
)
from knowledge.retrieval.vector_search import VectorSearchResult, VectorSearchService

__all__ = [
    "NomicEmbedder",
    "get_embedder",
    "VectorSearchService",
    "VectorSearchResult",
    "TenantSecurityError",
    "MissingTenantContextError",
    "TenantMismatchError",
    "InvalidVectorDimensionError",
]

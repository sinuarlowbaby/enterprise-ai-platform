"""
Knowledge & RAG Package.

Exposes document parsers, chunking splitters, embedding models,
and tenant-isolated vector search.
"""

from knowledge.chunking.splitter import Chunk, RecursiveTokenSplitter
from knowledge.parsers.base import BaseParser, BlockType, DocumentBlock, ParsedDocument
from knowledge.parsers.docx import DocxParser
from knowledge.parsers.factory import ParserFactory
from knowledge.parsers.markdown import MarkdownParser
from knowledge.parsers.pdf import PyMuPDFParser
from knowledge.parsers.text import TextParser
from knowledge.retrieval.embedder import NomicEmbedder, get_embedder
from knowledge.retrieval.exceptions import (
    InvalidVectorDimensionError,
    MissingTenantContextError,
    TenantMismatchError,
    TenantSecurityError,
)
from knowledge.retrieval.vector_search import VectorSearchResult, VectorSearchService

__all__ = [
    # Chunking
    "Chunk",
    "RecursiveTokenSplitter",
    # Parsers
    "BaseParser",
    "BlockType",
    "DocumentBlock",
    "ParsedDocument",
    "PyMuPDFParser",
    "DocxParser",
    "MarkdownParser",
    "TextParser",
    "ParserFactory",
    # Embedder & Retrieval
    "NomicEmbedder",
    "get_embedder",
    "VectorSearchService",
    "VectorSearchResult",
    # Security
    "TenantSecurityError",
    "MissingTenantContextError",
    "TenantMismatchError",
    "InvalidVectorDimensionError",
]

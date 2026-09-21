"""
Chunking Package.

Provides token-aware recursive text splitting with mandatory metadata attachment.
"""

from knowledge.chunking.splitter import Chunk, RecursiveTokenSplitter

__all__ = [
    "Chunk",
    "RecursiveTokenSplitter",
]

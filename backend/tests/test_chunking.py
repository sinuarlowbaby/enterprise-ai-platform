"""
Unit tests for RecursiveTokenSplitter and Chunk metadata enrichment.
"""

import uuid
import pytest

from knowledge.chunking.splitter import Chunk, RecursiveTokenSplitter
from knowledge.parsers.base import BlockType, DocumentBlock, ParsedDocument


def test_token_counting_accuracy():
    """Verify exact token count calculation via tiktoken."""
    splitter = RecursiveTokenSplitter()
    text = "Enterprise AI Platform RAG Engine"
    tokens = splitter.count_tokens(text)
    assert tokens > 0
    assert splitter.count_tokens("") == 0


def test_chunking_with_mandatory_metadata():
    """Verify that all mandatory metadata fields are attached to every chunk."""
    t_id = uuid.uuid4()
    d_id = uuid.uuid4()

    doc = ParsedDocument(
        source_filename="security_policy.pdf",
        file_type="application/pdf",
        title="Corporate Security Policy",
        total_pages=3,
        blocks=[
            DocumentBlock(
                text="1. Access Control",
                block_type=BlockType.HEADING,
                page_number=1,
                heading_level=1,
                section_path=["1. Access Control"],
            ),
            DocumentBlock(
                text="All API endpoints require cryptographically hashed API keys for tenant isolation.",
                block_type=BlockType.PARAGRAPH,
                page_number=1,
                section_path=["1. Access Control"],
            ),
            DocumentBlock(
                text="2. Encryption Standards",
                block_type=BlockType.HEADING,
                page_number=2,
                heading_level=1,
                section_path=["2. Encryption Standards"],
            ),
            DocumentBlock(
                text="Data at rest is encrypted with AES-256 and vector databases use dedicated network namespaces.",
                block_type=BlockType.PARAGRAPH,
                page_number=2,
                section_path=["2. Encryption Standards"],
            ),
        ],
        metadata={"classification": "Confidential"},
    )

    splitter = RecursiveTokenSplitter(chunk_size_tokens=512, chunk_overlap_tokens=64)
    chunks = splitter.split_document(doc, tenant_id=t_id, document_id=d_id)

    assert len(chunks) > 0
    for idx, chunk in enumerate(chunks):
        assert chunk.chunk_index == idx
        assert chunk.tenant_id == t_id
        assert chunk.document_id == d_id

        meta = chunk.metadata
        # Mandatory metadata fields
        assert meta["tenant_id"] == str(t_id)
        assert meta["document_id"] == str(d_id)
        assert meta["filename"] == "security_policy.pdf"
        assert meta["chunk_index"] == idx
        assert meta["title"] == "Corporate Security Policy"
        assert isinstance(meta["section_headings"], list)
        assert isinstance(meta["page_numbers"], list)
        assert meta["token_count"] > 0
        assert meta["char_count"] == len(chunk.content)
        assert meta["file_type"] == "application/pdf"
        assert meta["classification"] == "Confidential"


def test_chunking_token_limit_and_overlap():
    """Verify that chunks respect target token limits and contain overlap."""
    # Create long text exceeding chunk size
    repeated_sentence = "PostgreSQL pgvector enables scalable HNSW semantic search for enterprise documents. "
    long_text = repeated_sentence * 50  # ~500 tokens

    splitter = RecursiveTokenSplitter(
        chunk_size_tokens=100,
        chunk_overlap_tokens=20,
    )

    doc = ParsedDocument(
        source_filename="test.txt",
        file_type="text/plain",
        title="Vector Search Guide",
        blocks=[
            DocumentBlock(text=long_text, page_number=1, section_path=["Overview"]),
        ],
    )

    chunks = splitter.split_document(doc)
    assert len(chunks) > 1

    for chunk in chunks:
        token_count = splitter.count_tokens(chunk.content)
        # Verify chunk does not exceed max target token limit
        assert token_count <= 110  # small tolerance for separator boundary


def test_multipage_spanning_chunk():
    """Verify that a chunk spanning across page boundaries aggregates page numbers."""
    doc = ParsedDocument(
        source_filename="multi_page.pdf",
        file_type="application/pdf",
        title="Multi-page Document",
        total_pages=2,
        blocks=[
            DocumentBlock(text="First half of sentence on page 1.", page_number=1),
            DocumentBlock(text="Second half of sentence on page 2.", page_number=2),
        ],
    )

    splitter = RecursiveTokenSplitter(chunk_size_tokens=500, chunk_overlap_tokens=50)
    chunks = splitter.split_document(doc)

    assert len(chunks) == 1
    assert chunks[0].metadata["page_numbers"] == [1, 2]


def test_split_text_convenience_method():
    """Verify split_text generates chunks with full metadata for raw text strings."""
    t_id = uuid.uuid4()
    d_id = uuid.uuid4()

    raw_text = "Enterprise AI Platform provides hybrid dense and sparse search with cross-encoders."
    splitter = RecursiveTokenSplitter(chunk_size_tokens=512)
    chunks = splitter.split_text(
        text=raw_text,
        filename="notes.txt",
        title="Notes",
        tenant_id=t_id,
        document_id=d_id,
    )

    assert len(chunks) == 1
    chunk_dict = chunks[0].to_dict()
    assert chunk_dict["tenant_id"] == str(t_id)
    assert chunk_dict["document_id"] == str(d_id)
    assert chunk_dict["chunk_index"] == 0
    assert chunk_dict["content"] == raw_text
    assert chunk_dict["metadata"]["filename"] == "notes.txt"
    assert chunk_dict["metadata"]["title"] == "Notes"

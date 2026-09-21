"""
Unit tests for NomicEmbedder service.
"""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from app.core.config import settings
from knowledge.retrieval.embedder import NomicEmbedder, get_embedder


def test_nomic_embedder_defaults():
    """Verify embedder default properties and Nomic prefixes."""
    embedder = NomicEmbedder()
    assert embedder.model_name == "nomic-ai/nomic-embed-text-v1.5"
    assert embedder.dimension == 768
    assert embedder.document_prefix == "search_document: "
    assert embedder.query_prefix == "search_query: "
    assert embedder.normalize_embeddings is True


def test_nomic_prefix_formatting():
    """Verify that search_document: and search_query: prefixes are applied idempotently."""
    embedder = NomicEmbedder()

    # Document prefix formatting
    raw_doc = "Financial report for Q3 2026"
    prefixed_doc = embedder.format_document(raw_doc)
    assert prefixed_doc == "search_document: Financial report for Q3 2026"

    # Already prefixed document should not duplicate prefix
    assert embedder.format_document(prefixed_doc) == "search_document: Financial report for Q3 2026"

    # Query prefix formatting
    raw_query = "What were the net earnings in Q3?"
    prefixed_query = embedder.format_query(raw_query)
    assert prefixed_query == "search_query: What were the net earnings in Q3?"

    # Already prefixed query should not duplicate prefix
    assert embedder.format_query(prefixed_query) == "search_query: What were the net earnings in Q3?"


def test_embed_empty_documents():
    """Verify that passing an empty list returns an empty list without loading model."""
    embedder = NomicEmbedder()
    assert embedder.embed_documents([]) == []


def test_embed_documents_with_mocked_model():
    """Verify embed_documents passes properly formatted texts to model."""
    embedder = NomicEmbedder()
    mock_model = MagicMock()
    # Mock encoding returning 2 vectors of dimension 768
    mock_model.encode.return_value = np.zeros((2, 768), dtype=np.float32)
    embedder._model = mock_model

    docs = ["First paragraph", "Second paragraph"]
    result = embedder.embed_documents(docs)

    assert len(result) == 2
    assert len(result[0]) == 768
    mock_model.encode.assert_called_once_with(
        ["search_document: First paragraph", "search_document: Second paragraph"],
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
    )


def test_embed_query_with_mocked_model():
    """Verify embed_query passes query with search_query: prefix to model."""
    embedder = NomicEmbedder()
    mock_model = MagicMock()
    mock_model.encode.return_value = np.ones((1, 768), dtype=np.float32)
    embedder._model = mock_model

    result = embedder.embed_query("find relevant docs")

    assert len(result) == 768
    mock_model.encode.assert_called_once_with(
        ["search_query: find relevant docs"],
        normalize_embeddings=True,
        show_progress_bar=False,
    )


@pytest.mark.asyncio
async def test_async_embedding_methods():
    """Verify async aembed_documents and aembed_query offload to threadpool."""
    embedder = NomicEmbedder()
    mock_model = MagicMock()
    mock_model.encode.side_effect = [
        np.zeros((1, 768), dtype=np.float32),
        np.ones((1, 768), dtype=np.float32),
    ]
    embedder._model = mock_model

    doc_res = await embedder.aembed_documents(["Async doc"])
    assert len(doc_res) == 1
    assert len(doc_res[0]) == 768

    query_res = await embedder.aembed_query("Async query")
    assert len(query_res) == 768


def test_get_embedder_singleton():
    """Verify get_embedder returns a cached singleton."""
    e1 = get_embedder()
    e2 = get_embedder()
    assert e1 is e2
    assert isinstance(e1, NomicEmbedder)

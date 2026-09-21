"""
Unit tests for Tenant-Isolated Vector Search Service and Security Guardrails.
"""

from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from sqlalchemy.dialects import postgresql

from app.core.config import settings
from app.models.document_chunk import DocumentChunk
from knowledge.retrieval.exceptions import (
    InvalidVectorDimensionError,
    MissingTenantContextError,
    TenantMismatchError,
    TenantSecurityError,
)
from knowledge.retrieval.vector_search import VectorSearchResult, VectorSearchService


def test_missing_tenant_context_rejected():
    """Verify that vector search rejects queries without a tenant context."""
    service = VectorSearchService()

    # None tenant_id
    with pytest.raises(MissingTenantContextError, match="Mandatory tenant_id context is missing"):
        service.validate_tenant_context(None)

    # Empty string tenant_id
    with pytest.raises(MissingTenantContextError, match="tenant_id cannot be blank"):
        service.validate_tenant_context("")

    with pytest.raises(MissingTenantContextError, match="tenant_id cannot be blank"):
        service.validate_tenant_context("   ")


def test_invalid_uuid_format_rejected():
    """Verify that non-UUID strings are rejected with TenantSecurityError."""
    service = VectorSearchService()

    with pytest.raises(TenantSecurityError, match="Invalid tenant_id UUID format"):
        service.validate_tenant_context("not-a-valid-uuid")

    valid_id = uuid.uuid4()
    with pytest.raises(TenantSecurityError, match="Invalid caller_tenant_id UUID format"):
        service.validate_tenant_context(valid_id, caller_tenant_id="malformed-caller")


def test_tenant_mismatch_raises_unauthorized_exception():
    """Verify cross-tenant data access attempts raise TenantMismatchError."""
    service = VectorSearchService()
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    with pytest.raises(TenantMismatchError) as exc_info:
        service.validate_tenant_context(tenant_id=tenant_a, caller_tenant_id=tenant_b)

    assert str(tenant_b) in str(exc_info.value)
    assert str(tenant_a) in str(exc_info.value)


def test_valid_tenant_context_accepted():
    """Verify that matching and valid tenant contexts pass validation."""
    service = VectorSearchService()
    tenant = uuid.uuid4()

    # UUID object
    validated = service.validate_tenant_context(tenant, caller_tenant_id=tenant)
    assert validated == tenant

    # String format
    validated_str = service.validate_tenant_context(str(tenant), caller_tenant_id=str(tenant))
    assert validated_str == tenant


def test_vector_dimension_validation():
    """Verify that query vectors of incorrect dimension are rejected."""
    service = VectorSearchService()
    tenant = uuid.uuid4()

    # Wrong dimension: 512 instead of 768
    with pytest.raises(InvalidVectorDimensionError, match="got 512, expected 768"):
        service.build_search_query(tenant_id=tenant, query_vector=[0.1] * 512)


def test_query_builder_enforces_tenant_id_in_compiled_sql():
    """Verify that compiled SQL ALWAYS includes WHERE document_chunks.tenant_id = :tenant_id."""
    service = VectorSearchService()
    tenant = uuid.uuid4()
    query_vector = [0.01] * settings.EMBEDDING_DIMENSION

    stmt = service.build_search_query(
        tenant_id=tenant,
        query_vector=query_vector,
        top_k=7,
    )

    compiled_sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))

    # CRITICAL: Verify tenant_id isolation is guaranteed in the SQL statement
    assert "document_chunks.tenant_id =" in compiled_sql
    assert str(tenant) in compiled_sql
    # Verify cosine distance operator <=> is used
    assert "<=>" in compiled_sql
    # Verify ordering and limit
    assert "ORDER BY distance" in compiled_sql
    assert "LIMIT 7" in compiled_sql


def test_query_builder_with_document_ids_and_metadata_filter():
    """Verify optional document_ids and JSONB metadata filters compile properly."""
    service = VectorSearchService()
    tenant = uuid.uuid4()
    doc_1 = uuid.uuid4()
    doc_2 = uuid.uuid4()
    query_vector = [0.01] * settings.EMBEDDING_DIMENSION

    stmt = service.build_search_query(
        tenant_id=tenant,
        query_vector=query_vector,
        document_ids=[doc_1, doc_2],
        metadata_filter={"section": "Financials"},
        score_threshold=0.75,
        top_k=3,
    )

    compiled_sql = str(stmt.compile(dialect=postgresql.dialect()))

    assert "document_chunks.tenant_id =" in compiled_sql
    assert "document_chunks.document_id IN" in compiled_sql
    # JSONB contains operator in PostgreSQL is @>
    assert "@>" in compiled_sql or "metadata" in compiled_sql


@pytest.mark.asyncio
async def test_search_by_embedding_execution():
    """Verify search_by_embedding executes query and formats VectorSearchResult."""
    service = VectorSearchService()
    tenant = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    mock_chunk = MagicMock()
    mock_chunk.id = chunk_id
    mock_chunk.tenant_id = tenant
    mock_chunk.document_id = doc_id
    mock_chunk.chunk_index = 0
    mock_chunk.content = "Quarterly revenue was $15M."
    mock_chunk.metadata_ = {
        "page_numbers": [1],
        "section_headings": ["Revenue"],
    }

    # Raw distance: 0.15 -> similarity score: 1.0 - 0.15 = 0.85
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [(mock_chunk, 0.15)]
    mock_session.execute.return_value = mock_result

    results = await service.search_by_embedding(
        session=mock_session,
        query_vector=[0.05] * settings.EMBEDDING_DIMENSION,
        tenant_id=tenant,
        top_k=5,
    )

    assert len(results) == 1
    res = results[0]
    assert res.chunk_id == chunk_id
    assert res.tenant_id == tenant
    assert res.similarity_score == pytest.approx(0.85, abs=0.001)
    assert res.distance == 0.15
    assert res.content == "Quarterly revenue was $15M."
    assert res.page_numbers == [1]
    assert res.section_headings == ["Revenue"]


@pytest.mark.asyncio
async def test_search_by_text_validates_tenant_before_embedding():
    """Verify that unauthorized tenant context is rejected before computing embeddings."""
    mock_embedder = MagicMock()
    mock_embedder.aembed_query = AsyncMock(return_value=[0.1] * 768)
    service = VectorSearchService(embedder=mock_embedder)

    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    mock_session = AsyncMock()

    # Mismatched caller context should raise immediately
    with pytest.raises(TenantMismatchError):
        await service.search_by_text(
            session=mock_session,
            query_text="What were the net profits?",
            tenant_id=tenant_a,
            caller_tenant_id=tenant_b,
        )

    # Embedder must NOT have been called due to early rejection!
    mock_embedder.aembed_query.assert_not_called()
    mock_session.execute.assert_not_called()

"""
Tenant-Isolated Vector Search Service with Strict Metadata Filtering.

Enforces zero data leakage across multi-tenant boundaries by mandating
WHERE document_chunks.tenant_id = :tenant_id on every vector query,
supported by PostgreSQL HNSW and B-Tree partition indexes.
"""

from dataclasses import dataclass, field
from typing import Any
import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document_chunk import DocumentChunk
from knowledge.retrieval.embedder import NomicEmbedder, get_embedder
from knowledge.retrieval.exceptions import (
    InvalidVectorDimensionError,
    MissingTenantContextError,
    TenantMismatchError,
    TenantSecurityError,
)


@dataclass
class VectorSearchResult:
    """
    Ranked vector similarity search result.

    Attributes:
        chunk_id: UUID of the matched DocumentChunk.
        tenant_id: Tenant owner UUID.
        document_id: Parent Document UUID.
        chunk_index: Sequence index in document.
        content: Text passage content.
        similarity_score: Normalized similarity score in range [0.0, 1.0].
        distance: Raw cosine distance metric (<=>).
        metadata: JSONB chunk metadata dictionary.
        page_numbers: 1-indexed pages spanned by this chunk.
        section_headings: Section breadcrumb hierarchy.
    """
    chunk_id: uuid.UUID
    tenant_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    similarity_score: float
    distance: float
    metadata: dict[str, Any] = field(default_factory=dict)
    page_numbers: list[int] = field(default_factory=list)
    section_headings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializes result to dictionary representation."""
        return {
            "chunk_id": str(self.chunk_id),
            "tenant_id": str(self.tenant_id),
            "document_id": str(self.document_id),
            "chunk_index": self.chunk_index,
            "content": self.content,
            "similarity_score": round(self.similarity_score, 4),
            "distance": round(self.distance, 4),
            "metadata": self.metadata,
            "page_numbers": self.page_numbers,
            "section_headings": self.section_headings,
        }


class VectorSearchService:
    """
    Vector search service with mandatory tenant isolation.

    Guarantees:
    1. Zero cross-tenant data leakage: Every query mandates WHERE tenant_id = :tenant_id.
    2. Unauthorized exception guarding: Rejects queries missing valid tenant context.
    3. Caller context verification: Rejects queries where caller context != requested tenant.
    4. Exact dimension validation: Verifies query vectors match EMBEDDING_DIMENSION (768).
    """

    def __init__(self, embedder: NomicEmbedder | None = None) -> None:
        self.embedder = embedder or get_embedder()
        self.expected_dimension = settings.EMBEDDING_DIMENSION

    def validate_tenant_context(
        self,
        tenant_id: uuid.UUID | str | None,
        caller_tenant_id: uuid.UUID | str | None = None,
    ) -> uuid.UUID:
        """
        Validates tenant context and guards against unauthorized cross-tenant access.

        Args:
            tenant_id: Target tenant UUID for the vector query.
            caller_tenant_id: Authenticated caller's tenant UUID (from API key / JWT).

        Returns:
            Validated target tenant UUID.

        Raises:
            MissingTenantContextError: If tenant_id is None, empty, or whitespace.
            TenantSecurityError: If tenant_id or caller_tenant_id is not a valid UUID.
            TenantMismatchError: If caller context does not match requested tenant.
        """
        # 1. Missing context check
        if tenant_id is None:
            raise MissingTenantContextError("Vector query rejected: Mandatory tenant_id context is missing.")

        tenant_str = str(tenant_id).strip()
        if not tenant_str:
            raise MissingTenantContextError("Vector query rejected: tenant_id cannot be blank.")

        # 2. UUID format validation
        try:
            target_uuid = uuid.UUID(tenant_str)
        except (ValueError, AttributeError) as exc:
            raise TenantSecurityError(
                f"Vector query rejected: Invalid tenant_id UUID format: '{tenant_str}'."
            ) from exc

        # 3. Caller vs Target tenant mismatch check
        if caller_tenant_id is not None:
            caller_str = str(caller_tenant_id).strip()
            try:
                caller_uuid = uuid.UUID(caller_str)
            except (ValueError, AttributeError) as exc:
                raise TenantSecurityError(
                    f"Vector query rejected: Invalid caller_tenant_id UUID format: '{caller_str}'."
                ) from exc

            if caller_uuid != target_uuid:
                raise TenantMismatchError(
                    caller_tenant=str(caller_uuid),
                    target_tenant=str(target_uuid),
                )

        return target_uuid

    def build_search_query(
        self,
        tenant_id: uuid.UUID | str,
        query_vector: list[float],
        caller_tenant_id: uuid.UUID | str | None = None,
        top_k: int = 5,
        score_threshold: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
        document_ids: list[uuid.UUID | str] | None = None,
    ) -> Select:
        """
        Builds a security-enforced SQLAlchemy Select statement for vector search.

        Mandates:
            WHERE document_chunks.tenant_id = :tenant_id
        """
        # Validate tenant security
        validated_tenant_id = self.validate_tenant_context(tenant_id, caller_tenant_id)

        # Validate vector dimensions
        actual_dim = len(query_vector)
        if actual_dim != self.expected_dimension:
            raise InvalidVectorDimensionError(
                actual_dim=actual_dim,
                expected_dim=self.expected_dimension,
            )

        # Distance expression using cosine distance (<=>)
        distance_expr = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

        # Base query with MANDATORY tenant partition filter
        stmt = (
            select(DocumentChunk, distance_expr)
            .where(DocumentChunk.tenant_id == validated_tenant_id)
            .where(DocumentChunk.embedding.is_not(None))
        )

        # Optional document_ids filter
        if document_ids:
            doc_uuids = [uuid.UUID(str(d)) for d in document_ids]
            stmt = stmt.where(DocumentChunk.document_id.in_(doc_uuids))

        # Optional JSONB metadata contains filter (@>)
        if metadata_filter:
            stmt = stmt.where(DocumentChunk.metadata_.contains(metadata_filter))

        # Optional distance threshold (cosine_distance <= 1.0 - threshold)
        if score_threshold is not None:
            max_distance = max(0.0, 1.0 - score_threshold)
            stmt = stmt.where(distance_expr <= max_distance)

        # Order by distance ascending and apply limit
        stmt = stmt.order_by(distance_expr).limit(top_k)
        return stmt

    async def search_by_embedding(
        self,
        session: AsyncSession,
        query_vector: list[float],
        tenant_id: uuid.UUID | str,
        caller_tenant_id: uuid.UUID | str | None = None,
        top_k: int = 5,
        score_threshold: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
        document_ids: list[uuid.UUID | str] | None = None,
    ) -> list[VectorSearchResult]:
        """
        Executes a tenant-isolated vector search using a precomputed embedding vector.
        """
        stmt = self.build_search_query(
            tenant_id=tenant_id,
            query_vector=query_vector,
            caller_tenant_id=caller_tenant_id,
            top_k=top_k,
            score_threshold=score_threshold,
            metadata_filter=metadata_filter,
            document_ids=document_ids,
        )

        result = await session.execute(stmt)
        rows = result.all()

        search_results: list[VectorSearchResult] = []
        for chunk, distance in rows:
            dist_val = float(distance) if distance is not None else 1.0
            # Normalized similarity score for cosine: 1.0 - distance
            similarity = max(0.0, min(1.0, 1.0 - dist_val))

            if score_threshold is not None and similarity < score_threshold:
                continue

            chunk_meta = chunk.metadata_ or {}
            page_numbers = chunk_meta.get("page_numbers", [1])
            section_headings = chunk_meta.get("section_headings", [])

            search_results.append(
                VectorSearchResult(
                    chunk_id=chunk.id,
                    tenant_id=chunk.tenant_id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    similarity_score=similarity,
                    distance=dist_val,
                    metadata=chunk_meta,
                    page_numbers=page_numbers,
                    section_headings=section_headings,
                )
            )

        return search_results

    async def search_by_text(
        self,
        session: AsyncSession,
        query_text: str,
        tenant_id: uuid.UUID | str,
        caller_tenant_id: uuid.UUID | str | None = None,
        top_k: int = 5,
        score_threshold: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
        document_ids: list[uuid.UUID | str] | None = None,
    ) -> list[VectorSearchResult]:
        """
        Embeds a text query using Nomic Embed ('search_query: ' prefix) and executes
        the tenant-isolated vector search.
        """
        # Validate tenant security prior to any expensive embedding computation
        self.validate_tenant_context(tenant_id, caller_tenant_id)

        # Generate 768-dim query embedding
        query_vector = await self.embedder.aembed_query(query_text)

        return await self.search_by_embedding(
            session=session,
            query_vector=query_vector,
            tenant_id=tenant_id,
            caller_tenant_id=caller_tenant_id,
            top_k=top_k,
            score_threshold=score_threshold,
            metadata_filter=metadata_filter,
            document_ids=document_ids,
        )

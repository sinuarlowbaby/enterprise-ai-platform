"""
Document Chunk Model Definition.

Represents a text chunk partitioned from a document, paired with dense
vector embeddings for hybrid semantic search and JSONB metadata.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.tenant import Tenant


class DocumentChunk(Base):
    """
    Document chunk entity storing text content, vector embeddings, and metadata.
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION),
        nullable=True,
    )
    # The database column is named 'metadata'. In Python, mapped as 'metadata_'
    # to avoid conflict with SQLAlchemy DeclarativeBase.metadata.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Convenient alias for metadata_
    @property
    def chunk_metadata(self) -> dict[str, Any]:
        """Provides intuitive access to the JSONB metadata dictionary."""
        return self.metadata_

    @chunk_metadata.setter
    def chunk_metadata(self, value: dict[str, Any]) -> None:
        self.metadata_ = value

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="document_chunks",
    )
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

    __table_args__ = (
        Index("ix_document_chunks_tenant_doc", "tenant_id", "document_id"),
        Index("ix_document_chunks_doc_index", "document_id", "chunk_index"),
        Index("ix_document_chunks_metadata_gin", "metadata", postgresql_using="gin"),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk id={self.id} doc_id={self.document_id} "
            f"chunk_index={self.chunk_index}>"
        )

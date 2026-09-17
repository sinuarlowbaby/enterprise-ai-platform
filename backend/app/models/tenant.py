"""
Tenant Model Definition.

Represents an isolated tenant organization within the platform.
"""

from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.api_key import APIKey
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.llm_usage_log import LLMUsageLog


class Tenant(Base):
    """
    Tenant entity model representing an organization account.
    Serves as the root boundary for all multi-tenant isolation.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    plan_tier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="free",
        server_default="free",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Relationships to tenant-scoped resources
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    document_chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    llm_usage_logs: Mapped[list["LLMUsageLog"]] = relationship(
        "LLMUsageLog",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name!r} plan_tier={self.plan_tier!r}>"

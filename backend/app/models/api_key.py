"""
API Key Model Definition.

Represents authentication and quota authorization credentials for a tenant.
"""

from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class APIKey(Base):
    """
    API Key model for tenant authentication, rate limits, and quota enforcement.
    """

    __tablename__ = "api_keys"

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
    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    key_prefix: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
    )
    hashed_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    rate_limit_rpm: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
        server_default="60",
    )
    monthly_token_quota: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=1_000_000,
        server_default="1000000",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="api_keys",
    )

    def __repr__(self) -> str:
        return (
            f"<APIKey id={self.id} tenant_id={self.tenant_id} "
            f"key_prefix={self.key_prefix!r} rate_limit_rpm={self.rate_limit_rpm}>"
        )

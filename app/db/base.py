"""
Database Declarative Base and Model Registration.

Provides the foundational SQLAlchemy 2.0 DeclarativeBase for all models.
Imports all models so that `Base.metadata` contains the complete table schema
for Alembic autogeneration and metadata discovery.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass


# Import all models here so that Alembic and SQLAlchemy metadata discovery
# can reliably register all tables by importing app.db.base.Base
from app.models.tenant import Tenant  # noqa: E402, F401
from app.models.api_key import APIKey  # noqa: E402, F401
from app.models.document import Document  # noqa: E402, F401
from app.models.document_chunk import DocumentChunk  # noqa: E402, F401
from app.models.llm_usage_log import LLMUsageLog  # noqa: E402, F401

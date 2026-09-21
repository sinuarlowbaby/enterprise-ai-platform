"""
Database Declarative Base.

Provides the foundational SQLAlchemy 2.0 DeclarativeBase for all models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass

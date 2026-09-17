"""
Unit tests for PostgreSQL SQLAlchemy 2.0 ORM models and schema metadata.
"""

from decimal import Decimal
import uuid

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.core.config import settings
from app.db.base import Base
from app.models.api_key import APIKey
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.llm_usage_log import LLMUsageLog
from app.models.tenant import Tenant


def test_metadata_contains_all_five_tables():
    """Verify that all five tables are registered in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "tenants",
        "api_keys",
        "documents",
        "document_chunks",
        "llm_usage_logs",
    }
    assert expected_tables.issubset(table_names)


def test_tenant_model_structure():
    """Verify column definitions and constraints on Tenant table."""
    table = Base.metadata.tables["tenants"]
    assert "id" in table.columns
    assert "name" in table.columns
    assert "plan_tier" in table.columns
    assert "created_at" in table.columns
    assert "is_active" in table.columns

    assert table.columns["id"].primary_key is True
    assert table.columns["name"].unique is True or any(
        idx.unique and "name" in [c.name for c in idx.columns] for idx in table.indexes
    )
    assert table.columns["name"].nullable is False
    assert table.columns["plan_tier"].nullable is False
    assert table.columns["is_active"].nullable is False

    # Instantiate model instance
    tenant = Tenant(name="Acme Corp", plan_tier="enterprise")
    assert tenant.name == "Acme Corp"
    assert tenant.plan_tier == "enterprise"
    assert "Acme Corp" in repr(tenant)


def test_api_key_model_structure():
    """Verify column definitions, foreign keys, and defaults on APIKey table."""
    table = Base.metadata.tables["api_keys"]
    assert "id" in table.columns
    assert "tenant_id" in table.columns
    assert "hashed_key" in table.columns
    assert "rate_limit_rpm" in table.columns
    assert "monthly_token_quota" in table.columns
    assert "is_active" in table.columns
    assert "created_at" in table.columns

    # Foreign key check
    fk_targets = [fk.target_fullname for fk in table.columns["tenant_id"].foreign_keys]
    assert "tenants.id" in fk_targets

    # Model instantiation
    t_id = uuid.uuid4()
    key = APIKey(
        tenant_id=t_id,
        name="Production Key",
        key_prefix="eap_live_",
        hashed_key="argon2id$hashedstring",
        rate_limit_rpm=120,
        monthly_token_quota=5_000_000,
    )
    assert key.tenant_id == t_id
    assert key.rate_limit_rpm == 120
    assert key.monthly_token_quota == 5_000_000
    assert "eap_live_" in repr(key)


def test_document_model_structure():
    """Verify Document model columns, foreign keys, and indexes."""
    table = Base.metadata.tables["documents"]
    assert "id" in table.columns
    assert "tenant_id" in table.columns
    assert "filename" in table.columns
    assert "file_type" in table.columns
    assert "file_size" in table.columns
    assert "status" in table.columns
    assert "created_at" in table.columns
    assert "updated_at" in table.columns

    fk_targets = [fk.target_fullname for fk in table.columns["tenant_id"].foreign_keys]
    assert "tenants.id" in fk_targets

    t_id = uuid.uuid4()
    doc = Document(
        tenant_id=t_id,
        filename="q3_financials.pdf",
        file_type="application/pdf",
        file_size=2048576,
        status="uploaded",
    )
    assert doc.filename == "q3_financials.pdf"
    assert doc.file_size == 2048576
    assert "q3_financials.pdf" in repr(doc)


def test_document_chunk_model_and_pgvector():
    """Verify DocumentChunk pgvector embedding, JSONB metadata, and property alias."""
    table = Base.metadata.tables["document_chunks"]
    assert "id" in table.columns
    assert "tenant_id" in table.columns
    assert "document_id" in table.columns
    assert "chunk_index" in table.columns
    assert "content" in table.columns
    assert "embedding" in table.columns
    assert "metadata" in table.columns
    assert "created_at" in table.columns

    # Foreign key checks
    tenant_fk = [fk.target_fullname for fk in table.columns["tenant_id"].foreign_keys]
    doc_fk = [fk.target_fullname for fk in table.columns["document_id"].foreign_keys]
    assert "tenants.id" in tenant_fk
    assert "documents.id" in doc_fk

    # Model instantiation and property alias test
    t_id = uuid.uuid4()
    d_id = uuid.uuid4()
    chunk = DocumentChunk(
        tenant_id=t_id,
        document_id=d_id,
        chunk_index=0,
        content="Enterprise AI platform architecture overview...",
        embedding=[0.01] * settings.EMBEDDING_DIMENSION,
        metadata_={"page": 1, "section": "Executive Summary"},
    )
    assert chunk.chunk_index == 0
    assert len(chunk.embedding) == 768
    assert chunk.metadata_["page"] == 1
    # Check chunk_metadata alias
    assert chunk.chunk_metadata["section"] == "Executive Summary"

    # Modify via chunk_metadata setter
    chunk.chunk_metadata = {"page": 2, "updated": True}
    assert chunk.metadata_["page"] == 2
    assert chunk.metadata_["updated"] is True


def test_llm_usage_log_model_structure():
    """Verify LLMUsageLog token metrics, numeric cost, and latency."""
    table = Base.metadata.tables["llm_usage_logs"]
    assert "id" in table.columns
    assert "tenant_id" in table.columns
    assert "model_name" in table.columns
    assert "prompt_tokens" in table.columns
    assert "completion_tokens" in table.columns
    assert "total_cost_usd" in table.columns
    assert "latency_ms" in table.columns
    assert "timestamp" in table.columns

    t_id = uuid.uuid4()
    log = LLMUsageLog(
        tenant_id=t_id,
        model_name="gpt-4o",
        prompt_tokens=350,
        completion_tokens=120,
        total_cost_usd=Decimal("0.003500"),
        latency_ms=452.8,
    )
    assert log.model_name == "gpt-4o"
    assert log.prompt_tokens == 350
    assert log.completion_tokens == 120
    assert log.total_cost_usd == Decimal("0.003500")
    assert log.latency_ms == 452.8
    assert "gpt-4o" in repr(log)


def test_ddl_compilation_with_postgresql_dialect():
    """Verify that all tables compile cleanly to valid PostgreSQL DDL with vector and JSONB."""
    dialect = postgresql.dialect()
    for table_name in ["tenants", "api_keys", "documents", "document_chunks", "llm_usage_logs"]:
        table = Base.metadata.tables[table_name]
        ddl = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table_name}" in ddl

    # Verify vector column DDL
    chunk_ddl = str(CreateTable(Base.metadata.tables["document_chunks"]).compile(dialect=dialect))
    assert "VECTOR(768)" in chunk_ddl
    assert "JSONB" in chunk_ddl

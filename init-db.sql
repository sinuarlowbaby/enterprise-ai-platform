-- Create langfuse database if it does not exist
SELECT 'CREATE DATABASE langfuse'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langfuse')\gexec

-- Connect to app_db and enable pgvector & uuid extensions
\c app_db;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. Tenants Table
-- Multi-tenant isolation boundary
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    plan_tier VARCHAR(50) NOT NULL DEFAULT 'free',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    is_active BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS ix_tenants_name ON tenants (name);

-- ============================================================================
-- 2. API Keys Table
-- Tenant authentication, rate limits, and monthly quota
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100),
    key_prefix VARCHAR(16),
    hashed_key VARCHAR(255) NOT NULL UNIQUE,
    rate_limit_rpm INTEGER NOT NULL DEFAULT 60,
    monthly_token_quota BIGINT NOT NULL DEFAULT 1000000,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_api_keys_tenant_id ON api_keys (tenant_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_api_keys_hashed_key ON api_keys (hashed_key);

-- ============================================================================
-- 3. Documents Table
-- Knowledge base uploaded files and indexing status
-- ============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_documents_tenant_id ON documents (tenant_id);
CREATE INDEX IF NOT EXISTS ix_documents_status ON documents (status);
CREATE INDEX IF NOT EXISTS ix_documents_tenant_status ON documents (tenant_id, status);

-- ============================================================================
-- 4. Document Chunks Table
-- Text chunks with pgvector embeddings (768-dim) and JSONB metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_document_chunks_tenant_id ON document_chunks (tenant_id);
CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks (document_id);
CREATE INDEX IF NOT EXISTS ix_document_chunks_tenant_doc ON document_chunks (tenant_id, document_id);
CREATE INDEX IF NOT EXISTS ix_document_chunks_doc_index ON document_chunks (document_id, chunk_index);
CREATE INDEX IF NOT EXISTS ix_document_chunks_metadata_gin ON document_chunks USING gin (metadata);
CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- 5. LLM Usage Logs Table
-- Token metrics, latencies, and dollar cost audits
-- ============================================================================
CREATE TABLE IF NOT EXISTS llm_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.000000,
    latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_llm_usage_logs_tenant_id ON llm_usage_logs (tenant_id);
CREATE INDEX IF NOT EXISTS ix_llm_usage_logs_model_name ON llm_usage_logs (model_name);
CREATE INDEX IF NOT EXISTS ix_llm_usage_logs_timestamp ON llm_usage_logs (timestamp);
CREATE INDEX IF NOT EXISTS ix_llm_usage_logs_tenant_timestamp ON llm_usage_logs (tenant_id, timestamp);

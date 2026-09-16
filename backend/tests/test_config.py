"""Unit tests for app.core.config Settings module."""

import pytest
from app.core.config import Settings, get_settings, settings


def test_settings_singleton():
    """Verify that get_settings() returns a cached singleton instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
    assert settings is s1


def test_default_values():
    """Verify default configurations when initialized without overrides."""
    config = Settings(_env_file=None)
    assert config.PROJECT_NAME == "Enterprise AI Platform"
    assert config.VERSION == "0.1.0"
    assert config.ENVIRONMENT == "development"
    assert config.DEBUG is False
    assert config.API_V1_STR == "/api/v1"
    assert config.POSTGRES_USER == "postgres"
    assert config.POSTGRES_PORT == 5432
    assert config.QDRANT_PORT == 6333
    assert config.REDIS_PORT == 6379


def test_cors_origins_parsing():
    """Verify CORS origins parsing for strings, JSON lists, and lists."""
    # Comma-separated string
    c1 = Settings(_env_file=None, BACKEND_CORS_ORIGINS="http://test.com, http://example.com")
    assert c1.BACKEND_CORS_ORIGINS == ["http://test.com", "http://example.com"]

    # JSON formatted list string
    c2 = Settings(_env_file=None, BACKEND_CORS_ORIGINS='["http://alpha.com", "http://beta.com"]')
    assert c2.BACKEND_CORS_ORIGINS == ["http://alpha.com", "http://beta.com"]

    # Python list
    c3 = Settings(_env_file=None, BACKEND_CORS_ORIGINS=["http://gamma.com"])
    assert c3.BACKEND_CORS_ORIGINS == ["http://gamma.com"]


def test_async_database_url_property():
    """Verify async_database_url calculation and override behavior."""
    # When DATABASE_URL is explicitly set
    c1 = Settings(_env_file=None, DATABASE_URL="postgresql+asyncpg://usr:pwd@dbhost:5433/custom_db")
    assert c1.async_database_url == "postgresql+asyncpg://usr:pwd@dbhost:5433/custom_db"

    # When DATABASE_URL is None, computed from POSTGRES_* fields
    c2 = Settings(
        _env_file=None,
        DATABASE_URL=None,
        POSTGRES_USER="myuser",
        POSTGRES_PASSWORD="mypassword",
        POSTGRES_HOST="pgserver",
        POSTGRES_PORT=5432,
        POSTGRES_DB="platform",
    )
    assert c2.async_database_url == "postgresql+asyncpg://myuser:mypassword@pgserver:5432/platform"


def test_qdrant_connection_url_property():
    """Verify Qdrant connection URL calculation."""
    # Default host and port
    c1 = Settings(_env_file=None, QDRANT_HOST="qdrant.internal", QDRANT_PORT=6333)
    assert c1.qdrant_connection_url == "http://qdrant.internal:6333"

    # Explicit override via QDRANT_URL
    c2 = Settings(_env_file=None, QDRANT_URL="https://cloud.qdrant.io:6333")
    assert c2.qdrant_connection_url == "https://cloud.qdrant.io:6333"


def test_async_redis_url_property():
    """Verify Redis connection URL calculation."""
    # Explicit REDIS_URL
    c1 = Settings(_env_file=None, REDIS_URL="redis://custom-redis:6379/1")
    assert c1.async_redis_url == "redis://custom-redis:6379/1"

    # Computed with password
    c2 = Settings(
        _env_file=None,
        REDIS_URL=None,
        REDIS_HOST="redishost",
        REDIS_PORT=6379,
        REDIS_PASSWORD="secretpassword",
        REDIS_DB=2,
    )
    assert c2.async_redis_url == "redis://:secretpassword@redishost:6379/2"

    # Computed without password
    c3 = Settings(
        _env_file=None,
        REDIS_URL=None,
        REDIS_HOST="redishost",
        REDIS_PORT=6379,
        REDIS_PASSWORD="",
        REDIS_DB=0,
    )
    assert c3.async_redis_url == "redis://redishost:6379/0"


def test_observability_and_guardrail_defaults():
    """Verify Langfuse, Presidio, and model default configurations."""
    config = Settings(_env_file=None)
    assert config.ENABLE_PII_ANONYMIZATION is True
    assert config.PRESIDIO_SCORE_THRESHOLD == 0.6
    assert config.DEFAULT_LLM_MODEL == "gpt-4o"
    assert config.DEFAULT_EMBEDDING_MODEL == "sentence-transformers/all-mpnet-base-v2"
    assert config.EMBEDDING_DIMENSION == 768
    assert config.RATE_LIMIT_PER_MINUTE == 60
    assert config.DEFAULT_TENANT_MONTHLY_TOKEN_BUDGET == 1_000_000

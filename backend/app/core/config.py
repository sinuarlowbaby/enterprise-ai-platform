"""
Application Configuration Module.

Uses pydantic-settings to provide strongly-typed configuration loaded from
environment variables and .env files across the enterprise AI platform.
"""

from functools import lru_cache
import json
from typing import Any, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Enterprise AI Platform Settings.

    Loads strongly-typed environment variables with intelligent fallback defaults.
    Reads from local `.env` and parent directory `../.env` automatically.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # 1. General Application Settings
    # =========================================================================
    PROJECT_NAME: str = Field(
        default="Enterprise AI Platform",
        description="Name of the application project",
    )
    VERSION: str = Field(
        default="0.1.0",
        description="Application release version",
    )
    DESCRIPTION: str = Field(
        default="Enterprise AI Platform Backend - Multi-Tenant RAG, Agents, Guardrails & Observability",
        description="Application description",
    )
    API_V1_STR: str = Field(
        default="/api/v1",
        description="Prefix for version 1 API routes",
    )
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = Field(
        default="development",
        description="Deployment environment runtime mode",
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode and verbose tracebacks",
    )
    SECRET_KEY: str = Field(
        default="enterprise-ai-platform-insecure-secret-key-change-in-production",
        description="Cryptographic secret key for signing tokens and sessions",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24 * 8,  # 8 days
        description="JWT access token validity duration in minutes",
    )
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        description="Allowed CORS origin addresses",
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        """Parses CORS origins from comma-separated string, JSON list, or list."""
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    parsed = json.loads(v_stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [i.strip() for i in v_stripped.split(",") if i.strip()]
        elif isinstance(v, (list, tuple, set)):
            return [str(i).strip() for i in v if str(i).strip()]
        return v

    # =========================================================================
    # 2. PostgreSQL & Relational Database (asyncpg / SQLAlchemy)
    # =========================================================================
    POSTGRES_USER: str = Field(
        default="postgres",
        description="PostgreSQL username",
    )
    POSTGRES_PASSWORD: str = Field(
        default="postgres",
        description="PostgreSQL password",
    )
    POSTGRES_HOST: str = Field(
        default="localhost",
        description="PostgreSQL host address",
    )
    POSTGRES_PORT: int = Field(
        default=5432,
        description="PostgreSQL port number",
    )
    POSTGRES_DB: str = Field(
        default="app_db",
        description="PostgreSQL database name",
    )
    DATABASE_URL: str | None = Field(
        default=None,
        description="Async SQLAlchemy database connection string (asyncpg)",
    )

    @property
    def async_database_url(self) -> str:
        """Returns the asyncpg database connection URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # =========================================================================
    # 3. Dedicated Vector Search Engine (Qdrant)
    # =========================================================================
    QDRANT_HOST: str = Field(
        default="localhost",
        description="Qdrant service host address",
    )
    QDRANT_PORT: int = Field(
        default=6333,
        description="Qdrant REST API port number",
    )
    QDRANT_GRPC_PORT: int = Field(
        default=6334,
        description="Qdrant gRPC port number",
    )
    QDRANT_API_KEY: str | None = Field(
        default=None,
        description="Optional API key for authenticated Qdrant instances",
    )
    QDRANT_URL: str | None = Field(
        default=None,
        description="Custom Qdrant REST URL (overrides host and port)",
    )

    @property
    def qdrant_connection_url(self) -> str:
        """Returns the HTTP endpoint for Qdrant REST API."""
        if self.QDRANT_URL:
            return self.QDRANT_URL
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    # =========================================================================
    # 4. Cache & Agent State Store (Redis)
    # =========================================================================
    REDIS_HOST: str = Field(
        default="localhost",
        description="Redis host address",
    )
    REDIS_PORT: int = Field(
        default=6379,
        description="Redis port number",
    )
    REDIS_PASSWORD: str = Field(
        default="redispassword",
        description="Redis auth password",
    )
    REDIS_DB: int = Field(
        default=0,
        description="Redis database index",
    )
    REDIS_URL: str | None = Field(
        default=None,
        description="Complete Redis connection URI",
    )

    @property
    def async_redis_url(self) -> str:
        """Returns the Redis connection URL."""
        if self.REDIS_URL:
            return self.REDIS_URL
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # =========================================================================
    # 5. LLM Observability & Tracing (Langfuse)
    # =========================================================================
    LANGFUSE_PUBLIC_KEY: str = Field(
        default="pk-lf-placeholder",
        description="Langfuse public project API key",
    )
    LANGFUSE_SECRET_KEY: str = Field(
        default="sk-lf-placeholder",
        description="Langfuse secret API key",
    )
    LANGFUSE_HOST: str = Field(
        default="http://localhost:3000",
        description="Langfuse backend host URL",
    )
    LANGFUSE_NEXTAUTH_SECRET: str = Field(
        default="changeme_to_a_random_32_char_secret_key",
        description="NextAuth secret for Langfuse self-hosted UI",
    )
    LANGFUSE_SALT: str = Field(
        default="changeme_to_a_random_salt_key",
        description="Salt key for Langfuse self-hosted auth",
    )
    LANGFUSE_ENCRYPTION_KEY: str = Field(
        default="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        description="64-char hex key for Langfuse database encryption",
    )

    # =========================================================================
    # 6. LLM & Embedding Models
    # =========================================================================
    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="OpenAI API key for LLM calls and embeddings",
    )
    OPENAI_BASE_URL: str | None = Field(
        default=None,
        description="Custom OpenAI-compatible API base URL (e.g. vLLM, Ollama)",
    )
    DEFAULT_LLM_MODEL: str = Field(
        default="gpt-4o",
        description="Default LLM model identifier",
    )
    DEFAULT_EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-mpnet-base-v2",
        description="Default text embedding model identifier",
    )
    EMBEDDING_DIMENSION: int = Field(
        default=768,
        description="Dimension size of default embeddings",
    )

    # =========================================================================
    # 7. Security, PII Guardrails & Limits
    # =========================================================================
    ENABLE_PII_ANONYMIZATION: bool = Field(
        default=True,
        description="Enable Presidio PII scanning and anonymization on prompts",
    )
    PRESIDIO_SCORE_THRESHOLD: float = Field(
        default=0.6,
        description="Confidence threshold for PII entity detection (0.0 to 1.0)",
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        description="Global default request rate limit per minute per tenant",
    )
    DEFAULT_TENANT_MONTHLY_TOKEN_BUDGET: int = Field(
        default=1_000_000,
        description="Default token budget allocated to new tenants monthly",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Creates and returns a cached singleton instance of the application Settings.
    """
    return Settings()


settings: Settings = get_settings()

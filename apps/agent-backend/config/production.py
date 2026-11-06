"""Production Cloud Infrastructure & Configuration Settings.

Handles:
- PostgreSQL (Supabase / Neon with connection pooling & SSL mode)
- Qdrant Cloud (TLS host, API key, 1536-dim collections)
- Upstash Redis (rediss:// TLS broker & session cache)
- E2B Code Sandbox API key
- Langfuse Telemetry keys & host
- Cloud environment verification & validation
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProductionSettings(BaseSettings):
    """Production Cloud Settings with strict connection strings and cloud secret integration."""

    # Project metadata
    PROJECT_NAME: str = "Agentic Workspace Backend"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    NODE_ENV: str = "production"

    # 1. PostgreSQL (Supabase / Neon with Connection Pooling)
    # Typically: postgresql://[user]:[password]@[host]:6543/[dbname]?pgbouncer=true&sslmode=require
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/agentic_workspace?sslmode=require",
        description="Pooled PostgreSQL connection URI (Neon / Supabase Transaction pooler)",
    )
    DIRECT_URL: Optional[str] = Field(
        default=None,
        description="Direct unpooled PostgreSQL URI for Prisma migrations and schema push",
    )
    DB_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Database pool max overflow")

    # 2. Qdrant Cloud (TLS host & API key)
    # Typically: https://xyz-cluster.eu-central.aws.cloud.qdrant.io:6333
    QDRANT_URL: str = Field(
        default="https://localhost:6333",
        description="Qdrant Cloud cluster endpoint with HTTPS/TLS",
    )
    QDRANT_API_KEY: Optional[str] = Field(
        default=None,
        description="Qdrant Cloud cluster API key",
    )
    QDRANT_COLLECTION_NAME: str = Field(
        default="workspace_documents",
        description="Primary vector search collection name",
    )
    QDRANT_VECTOR_DIM: int = Field(
        default=1536,
        description="Vector dimension (e.g. 1536 for text-embedding-3-small/ada-002)",
    )

    # 3. Upstash Redis (rediss:// TLS broker & session cache)
    # Typically: rediss://default:[token]@[endpoint].upstash.io:6379
    REDIS_URL: str = Field(
        default="rediss://localhost:6379/0",
        description="TLS-secured Redis connection URI (Upstash)",
    )

    # 4. E2B Cloud Code Sandbox API Key
    E2B_API_KEY: Optional[str] = Field(
        default=None,
        description="E2B Sandbox API key for secure cloud execution containers",
    )

    # 5. Langfuse Observability & Telemetry Keys
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(
        default=None,
        description="Langfuse public project key",
    )
    LANGFUSE_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Langfuse secret API key",
    )
    LANGFUSE_HOST: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse Cloud or self-hosted endpoint",
    )

    # LLM Providers (Cloud Secrets)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_GEMINI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None

    # Platform Security
    JWT_SECRET: str = Field(
        default="super-secret-jwt-token-key-change-in-production-32-chars-min",
        description="Secret key for JWT validation",
    )
    ALGORITHM: str = "HS256"
    WEB_CONCURRENCY: int = Field(default=4, description="Uvicorn worker concurrency")

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        # Normalize postgres:// to postgresql:// if passed by cloud providers
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    model_config = SettingsConfigDict(
        env_file=(".env.production", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


production_settings = ProductionSettings()


from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Agentic Workspace Backend"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Environment
    NODE_ENV: str = "development"

    # CORS — Comma-separated frontend origins for production/staging
    # e.g. "https://app.agentic-void.io,https://staging.agentic-void.io"
    FRONTEND_URL: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/agentic_workspace?schema=public"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None

    # LLM Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_GEMINI_API_KEY: Optional[str] = None

    # Security
    JWT_SECRET: str = "super-secret-jwt-token-key-change-in-production-32-chars-min"
    ALGORITHM: str = "HS256"

    @property
    def cors_origins(self) -> list[str]:
        """Parse FRONTEND_URL into a list of allowed origins."""
        origins = [o.strip() for o in self.FRONTEND_URL.split(",") if o.strip()]
        # Always include API server itself for local dev & Swagger UI
        for extra in ["http://localhost:8000", "http://127.0.0.1:8000"]:
            if extra not in origins:
                origins.append(extra)
        return origins

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

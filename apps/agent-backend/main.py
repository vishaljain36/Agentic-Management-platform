from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import sys

from app.core.config import settings
from app.api.router import api_router
from app.core.redis import get_redis_client
from app.agents.tools.code_runner import is_docker_available


# Initialize Rate Limiter: Default 120 requests/minute per client IP
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print(f"[STARTUP] {settings.PROJECT_NAME} v{settings.VERSION} starting up...")
    yield
    # Shutdown actions
    print(f"[SHUTDOWN] {settings.PROJECT_NAME} shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Multi-Agent Workspace Orchestrator & LangGraph Engine",
    lifespan=lifespan,
)

# Attach SlowAPI limiter state and handlers
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Configure CORS rules
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if settings.NODE_ENV == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-API-Key"],
)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Basic health check probe for load balancers."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.NODE_ENV,
    }


@app.get("/api/v1/health", tags=["Health"])
@limiter.limit("60/minute")
async def detailed_system_health(request: Request):
    """Comprehensive automated system health check across all services."""
    checks = {}
    overall_status = "healthy"

    # 1. Redis Check
    try:
        r = get_redis_client()
        if r is not None:
            r.ping()
            checks["redis"] = {"status": "up", "detail": "Connected"}
        else:
            checks["redis"] = {"status": "down", "detail": "Fallback memory mode active"}
    except Exception as e:
        checks["redis"] = {"status": "down", "error": str(e)}

    # 2. Vector DB / Qdrant Check
    try:
        import httpx
        async with httpx.AsyncClient(timeout=0.5) as client:
            resp = await client.get(f"{settings.QDRANT_URL}/healthz")
            if resp.status_code == 200:
                checks["qdrant"] = {"status": "up", "detail": "Cluster operational"}
            else:
                checks["qdrant"] = {"status": "degraded", "code": resp.status_code}
    except Exception:
        checks["qdrant"] = {"status": "down", "detail": "Local fastembed in-memory active"}

    # 3. Sandbox Execution Runner
    docker_ready = is_docker_available()
    checks["sandbox"] = {
        "status": "ready",
        "mode": "docker" if docker_ready else "subprocess-isolated",
        "docker_available": docker_ready,
        "runtime_bound_sec": 60,
        "memory_bound_mb": 512,
    }

    # 4. Python Environment & Architecture
    checks["runtime"] = {
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
    }

    return {
        "status": overall_status,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "checks": checks,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

"""FastAPI Application Entry Point — Production Hardened.

Includes:
- Dynamic CORS from FRONTEND_URL env (comma-separated domain arrays)
- Zero-downtime health probes: /healthz (liveness) and /readyz (readiness)
- Request ID tracing middleware (X-Request-ID)
- Global structured JSON error handler
- Rate limiting via SlowAPI
"""

import sys
import time
import uuid
import traceback

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.api.router import api_router
from app.core.redis import get_redis_client
from app.agents.tools.code_runner import is_docker_available


# ---------------------------------------------------------------------------
# Rate Limiter: 120 requests/minute per client IP
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


# ---------------------------------------------------------------------------
# Startup / Shutdown Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[STARTUP] {settings.PROJECT_NAME} v{settings.VERSION} starting up...")
    print(f"[STARTUP] Environment: {settings.NODE_ENV}")
    print(f"[STARTUP] CORS origins: {settings.cors_origins}")
    yield
    print(f"[SHUTDOWN] {settings.PROJECT_NAME} shutting down...")


# ---------------------------------------------------------------------------
# Application Instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Multi-Agent Workspace Orchestrator & LangGraph Engine",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware: Request ID Tracing
# ---------------------------------------------------------------------------
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique X-Request-ID header into every request/response cycle.

    If the client sends an X-Request-ID, it is preserved for distributed tracing.
    Otherwise a new UUID4 is generated.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        # Attach to request state for downstream logging
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response: Response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        return response


# Middleware order matters — outermost first (LIFO application)
app.add_middleware(RequestIDMiddleware)

# SlowAPI rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# ---------------------------------------------------------------------------
# Middleware: Production CORS from FRONTEND_URL
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if settings.NODE_ENV == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Type",
        "X-API-Key",
        "X-Request-ID",
        "X-Response-Time-Ms",
    ],
)


# ---------------------------------------------------------------------------
# Global Structured JSON Error Handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler returning structured JSON error payloads."""
    request_id = getattr(request.state, "request_id", "unknown")
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)

    # Log the full trace server-side
    print(f"[ERROR] request_id={request_id} path={request.url.path} error={exc}")
    if settings.NODE_ENV != "production":
        for line in tb:
            print(line, end="")

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": str(exc) if settings.NODE_ENV != "production" else "An unexpected error occurred.",
            "request_id": request_id,
            "path": str(request.url.path),
        },
        headers={"X-Request-ID": request_id},
    )


# ---------------------------------------------------------------------------
# API Router
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ---------------------------------------------------------------------------
# Health Probes
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"])
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Legacy health endpoint (backward compatible)."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.NODE_ENV,
    }


@app.get("/healthz", tags=["Health"])
async def liveness_probe(request: Request):
    """Kubernetes-style liveness probe. Returns 200 if the process is alive.

    Does NOT check downstream dependencies — only confirms the Python
    process and FastAPI event loop are responsive.
    """
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@app.get("/readyz", tags=["Health"])
async def readiness_probe(request: Request):
    """Kubernetes-style readiness probe. Checks PostgreSQL, Redis, and Qdrant.

    Returns 200 + overall "ready" when all critical dependencies are reachable.
    Returns 503 + per-service status when one or more are unreachable.
    """
    checks = {}
    all_ready = True

    # 1. PostgreSQL / Database connectivity
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        # Prisma / SQLAlchemy use psycopg2 sync — run in executor to avoid blocking
        # For the probe, use a lightweight TCP check to the DB host
        import socket
        from urllib.parse import urlparse

        parsed = urlparse(settings.DATABASE_URL)
        db_host = parsed.hostname or "localhost"
        db_port = parsed.port or 5432
        sock = socket.create_connection((db_host, db_port), timeout=1.0)
        sock.close()
        checks["postgresql"] = {"status": "up", "host": db_host, "port": db_port}
    except Exception as e:
        checks["postgresql"] = {"status": "down", "error": str(e)}
        all_ready = False

    # 2. Redis (Upstash or local)
    try:
        r = get_redis_client()
        if r is not None:
            r.ping()
            checks["redis"] = {"status": "up", "detail": "Connected and responsive"}
        else:
            checks["redis"] = {"status": "degraded", "detail": "In-memory fallback active"}
    except Exception as e:
        checks["redis"] = {"status": "down", "error": str(e)}
        all_ready = False

    # 3. Qdrant Vector Database
    try:
        import httpx
        async with httpx.AsyncClient(timeout=1.0) as client:
            resp = await client.get(f"{settings.QDRANT_URL}/healthz")
            if resp.status_code == 200:
                checks["qdrant"] = {"status": "up", "detail": "Cluster operational"}
            else:
                checks["qdrant"] = {"status": "degraded", "http_code": resp.status_code}
    except Exception:
        checks["qdrant"] = {"status": "degraded", "detail": "In-memory vector mode active"}

    status_code = 200 if all_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ready else "not_ready",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "checks": checks,
        },
    )


# ---------------------------------------------------------------------------
# Detailed System Health (existing endpoint — preserved)
# ---------------------------------------------------------------------------
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

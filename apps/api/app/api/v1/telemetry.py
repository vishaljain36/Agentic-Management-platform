"""Admin Telemetry & Observability Dashboard Endpoints.

Provides:
- GET /api/v1/admin/telemetry/metrics:
  Returns real-time Redis queue latency, active WebSocket / SSE connections,
  and aggregated LLM token expenditure.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from orchestrator.tracing import telemetry_manager
from app.core.redis import get_redis_client

router = APIRouter()


class RedisMetrics(BaseModel):
    status: str
    latency_ms: float
    queue_depth: int


class ConnectionMetrics(BaseModel):
    active_websockets: int
    active_sse_streams: int
    total_active: int


class LlmExpenditureMetrics(BaseModel):
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float
    currency: str = "USD"
    total_steps_executed: int


class TelemetryDashboardResponse(BaseModel):
    status: str
    timestamp: str
    redis: RedisMetrics
    connections: ConnectionMetrics
    llm_expenditure: LlmExpenditureMetrics
    spans: Dict[str, Any]


@router.get("/metrics", response_model=TelemetryDashboardResponse)
async def get_telemetry_metrics():
    """Return real-time cluster telemetry, Redis latency, active streams, and LLM expenditure."""
    # 1. Measure Redis latency & queue depth
    redis_status = "connected"
    queue_depth = 0
    t0 = time.perf_counter()
    try:
        redis_client = get_redis_client()
        if hasattr(redis_client, "ping"):
            redis_client.ping()
        if hasattr(redis_client, "llen"):
            try:
                queue_depth = redis_client.llen("celery")
            except Exception:
                queue_depth = 0
        redis_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as exc:
        redis_status = "degraded"
        redis_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # 2. Extract telemetry manager stats
    current_metrics = telemetry_manager.get_metrics()

    return TelemetryDashboardResponse(
        status="healthy" if redis_status == "connected" else "degraded",
        timestamp=datetime.now(timezone.utc).isoformat(),
        redis=RedisMetrics(
            status=redis_status,
            latency_ms=redis_latency_ms,
            queue_depth=queue_depth,
        ),
        connections=ConnectionMetrics(
            active_websockets=current_metrics["connections"]["active_websockets"],
            active_sse_streams=current_metrics["connections"]["active_sse_streams"],
            total_active=current_metrics["connections"]["total_active"],
        ),
        llm_expenditure=LlmExpenditureMetrics(
            total_input_tokens=current_metrics["llm_expenditure"]["total_input_tokens"],
            total_output_tokens=current_metrics["llm_expenditure"]["total_output_tokens"],
            total_tokens=current_metrics["llm_expenditure"]["total_tokens"],
            total_cost_usd=current_metrics["llm_expenditure"]["total_cost_usd"],
            currency="USD",
            total_steps_executed=current_metrics["llm_expenditure"]["total_steps_executed"],
        ),
        spans=current_metrics["spans"],
    )


@router.post("/metrics/reset")
async def reset_telemetry_metrics():
    """Reset telemetry metrics (used by test suites)."""
    telemetry_manager.reset_metrics()
    return {"status": "RESET", "message": "Telemetry metrics reset successfully"}


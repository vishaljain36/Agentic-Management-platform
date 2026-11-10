"""Pytest Fixtures for Backend Isolated Test Suite (Pytest & HTTPX).

Provides:
- HTTPX AsyncClient fixture for FastAPI endpoints with ASGI transport.
- Eager Celery worker fixture configuring task_always_eager = True.
- Telemetry manager state reset fixture.
"""

import os
import sys
from pathlib import Path
import pytest
import httpx

# Ensure apps/api root is on sys.path
api_root = str(Path(__file__).parent.parent.resolve())
if api_root not in sys.path:
    sys.path.insert(0, api_root)

from main import app
from workers.celery_app import celery_app
from orchestrator.tracing import telemetry_manager


@pytest.fixture
async def async_client():
    """HTTPX AsyncClient configured with ASGI transport against the FastAPI app."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client


@pytest.fixture
def eager_celery():
    """Configure Celery in eager execution mode for unit/integration testing."""
    prev_eager = celery_app.conf.task_always_eager
    prev_propagate = celery_app.conf.task_eager_propagates
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    try:
        yield celery_app
    finally:
        celery_app.conf.task_always_eager = prev_eager
        celery_app.conf.task_eager_propagates = prev_propagate


@pytest.fixture(autouse=True)
def clean_telemetry():
    """Reset OpenTelemetry in-memory span collector and metric counters before each test."""
    telemetry_manager.reset_metrics()
    telemetry_manager.collector.clear()
    yield
    telemetry_manager.reset_metrics()
    telemetry_manager.collector.clear()


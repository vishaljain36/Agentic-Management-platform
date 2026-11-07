"""Unit and integration tests for Phase 9: Telemetry, Tracing & Application Observability.

Verifies:
1. Multi-agent state graph execution generates valid OpenTelemetry spans with prompt inputs/outputs,
   model latency, token counts, and step costs.
2. Error tracking captures unhandled exceptions via OpenTelemetry and Sentry.
3. Admin telemetry metrics endpoint (/api/v1/admin/telemetry/metrics) returns real-time stats.
4. Active WebSocket and SSE connection counters gauge streaming sessions.
5. Token count estimation and resale cost calculation precision.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from orchestrator.tracing import (
    telemetry_manager,
    trace_agent_node,
    calculate_step_cost,
    estimate_tokens_from_text,
    RATE_INPUT_PER_1K,
    RATE_OUTPUT_PER_1K,
)
from orchestrator.agent_graph import MultiAgentOrchestrator
from opentelemetry.trace import StatusCode


@pytest.fixture(autouse=True)
def reset_telemetry():
    """Reset telemetry metrics and captured spans before each test."""
    telemetry_manager.reset_metrics()
    yield
    telemetry_manager.reset_metrics()


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Multi-Agent Execution OpenTelemetry Tracing
# ---------------------------------------------------------------------------

def test_multi_agent_execution_generates_valid_spans():
    """Execute multi-agent workflow and verify all nodes generate valid OTel spans."""
    orchestrator = MultiAgentOrchestrator()
    prompt = "Perform deep security architecture analysis of distributed microservices."

    result = orchestrator.execute_workflow(prompt=prompt, thread_id="test_simulated_run_101")
    assert result is not None

    spans = telemetry_manager.collector.get_spans()
    assert len(spans) >= 4, f"Expected at least 4 spans, got {len(spans)}"

    span_names = [s.name for s in spans]
    assert any("researcher_node" in name for name in span_names)
    assert any("evaluator_node" in name for name in span_names)
    assert any("final_writer_node" in name for name in span_names)
    assert any("agent_execution_loop" in name for name in span_names)

    # Validate detailed span attributes on researcher node
    researcher_span = next(s for s in spans if "researcher_node" in s.name)
    attrs = researcher_span.attributes

    assert "gen_ai.prompt.input" in attrs
    assert "security architecture" in attrs["gen_ai.prompt.input"]
    assert "gen_ai.prompt.output" in attrs
    assert "[Researcher]" in attrs["gen_ai.prompt.output"]
    assert attrs["gen_ai.latency_ms"] >= 0.0
    assert attrs["gen_ai.usage.input_tokens"] > 0
    assert attrs["gen_ai.usage.output_tokens"] > 0
    assert attrs["gen_ai.usage.total_tokens"] == attrs["gen_ai.usage.input_tokens"] + attrs["gen_ai.usage.output_tokens"]
    assert attrs["gen_ai.step_cost_usd"] > 0.0
    assert researcher_span.status.status_code == StatusCode.OK


def test_hitl_workflow_interruption_and_approval_spans():
    """Verify that human approval checkpoint generates appropriate span."""
    orchestrator = MultiAgentOrchestrator()
    prompt = "Trigger database schema exec mutation."

    result = orchestrator.execute_workflow(prompt=prompt, thread_id="test_hitl_span_run", requires_approval=True)
    assert result is not None

    spans = telemetry_manager.collector.get_spans()
    span_names = [s.name for s in spans]
    assert any("human_approval_node" in name for name in span_names)

    approval_span = next(s for s in spans if "human_approval_node" in s.name)
    assert approval_span.status.status_code == StatusCode.OK
    assert "[HITL Approved]" in approval_span.attributes["gen_ai.prompt.output"]


# ---------------------------------------------------------------------------
# 2. Token Estimation & Cost Precision
# ---------------------------------------------------------------------------

def test_token_and_cost_calculation():
    """Verify hybrid resale pricing: $0.003/1k in + $0.012/1k out."""
    cost = calculate_step_cost(input_tokens=1000, output_tokens=1000)
    expected = round(RATE_INPUT_PER_1K + RATE_OUTPUT_PER_1K, 6)
    assert cost == expected == 0.015

    # Asymmetric test
    cost_asym = calculate_step_cost(input_tokens=2000, output_tokens=500)
    expected_asym = round((2 * 0.003) + (0.5 * 0.012), 6)
    assert cost_asym == expected_asym == 0.012


def test_token_estimation_heuristics():
    """Verify text to token estimation handles empty, strings, and dictionaries."""
    assert estimate_tokens_from_text("") == 0
    assert estimate_tokens_from_text(None) == 0
    assert estimate_tokens_from_text("hello world") >= 2
    assert estimate_tokens_from_text({"key": "value", "count": 100}) > 0


# ---------------------------------------------------------------------------
# 3. Error Tracking & Sentry / OTel Span Failure Logging
# ---------------------------------------------------------------------------

def test_exception_in_agent_node_recorded_on_span_and_sentry():
    """Verify exceptions are captured on OTel spans with ERROR status and forwarded to Sentry."""
    @trace_agent_node(node_name="failing_agent_node", agent_type="agent")
    def faulty_agent(state):
        raise ValueError("Simulated LLM context window exceeded")

    with patch("sentry_sdk.capture_exception") as mock_sentry:
        with pytest.raises(ValueError) as exc_info:
            faulty_agent({"prompt": "crash test"})

        assert "Simulated LLM context window exceeded" in str(exc_info.value)
        # Sentry should be called
        mock_sentry.assert_called_once()

    spans = telemetry_manager.collector.get_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.status.status_code == StatusCode.ERROR
    assert "Simulated LLM context window exceeded" in span.status.description


# ---------------------------------------------------------------------------
# 4. Observability Dashboard Admin API Route
# ---------------------------------------------------------------------------

def test_admin_telemetry_metrics_endpoint(client):
    """Verify GET /api/v1/admin/telemetry/metrics returns 200 with structured metrics."""
    # Seed some metrics
    orchestrator = MultiAgentOrchestrator()
    orchestrator.execute_workflow("Dashboard metrics seeding", thread_id="seed_thread")

    response = client.get("/api/v1/admin/telemetry/metrics")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]
    assert "timestamp" in data

    # Redis metrics
    assert "redis" in data
    assert data["redis"]["status"] in ["connected", "degraded"]
    assert data["redis"]["latency_ms"] >= 0.0
    assert "queue_depth" in data["redis"]

    # Connections metrics
    assert "connections" in data
    assert data["connections"]["active_websockets"] == 0
    assert data["connections"]["active_sse_streams"] == 0
    assert data["connections"]["total_active"] == 0

    # LLM expenditure metrics
    assert "llm_expenditure" in data
    assert data["llm_expenditure"]["total_input_tokens"] > 0
    assert data["llm_expenditure"]["total_output_tokens"] > 0
    assert data["llm_expenditure"]["total_cost_usd"] > 0.0
    assert data["llm_expenditure"]["currency"] == "USD"
    assert data["llm_expenditure"]["total_steps_executed"] >= 4

    # Spans metrics
    assert "spans" in data
    assert data["spans"]["total_recorded_spans"] >= 4


def test_admin_telemetry_metrics_reset(client):
    """Verify POST /api/v1/admin/telemetry/metrics/reset clears state."""
    orchestrator = MultiAgentOrchestrator()
    orchestrator.execute_workflow("Metrics to be reset", thread_id="reset_thread")

    resp1 = client.get("/api/v1/admin/telemetry/metrics")
    assert resp1.json()["llm_expenditure"]["total_input_tokens"] > 0

    reset_resp = client.post("/api/v1/admin/telemetry/metrics/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "RESET"

    resp2 = client.get("/api/v1/admin/telemetry/metrics")
    assert resp2.json()["llm_expenditure"]["total_input_tokens"] == 0
    assert resp2.json()["spans"]["total_recorded_spans"] == 0


# ---------------------------------------------------------------------------
# 5. Connection Gauging (Active WebSocket & SSE Streams)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_active_connection_gauges_lifecycle():
    """Verify async context managers correctly increment and decrement active gauges."""
    assert telemetry_manager.active_sse_streams == 0
    assert telemetry_manager.active_websockets == 0

    async with telemetry_manager.track_sse():
        assert telemetry_manager.active_sse_streams == 1
        async with telemetry_manager.track_ws():
            assert telemetry_manager.active_websockets == 1
            metrics = telemetry_manager.get_metrics()
            assert metrics["connections"]["total_active"] == 2

        assert telemetry_manager.active_websockets == 0

    assert telemetry_manager.active_sse_streams == 0


def test_websocket_workflow_run_endpoint(client):
    """Verify WebSocket endpoint connects, increments gauge, responds to messages, and closes cleanly."""
    with client.websocket_connect("/api/v1/workflow/ws/ws_test_run") as websocket:
        # Connected event received
        init_data = websocket.receive_json()
        assert init_data["event"] == "connected"
        assert init_data["run_id"] == "ws_test_run"

        # Send command
        websocket.send_text("PING_ORCHESTRATOR")
        ack_data = websocket.receive_json()
        assert ack_data["event"] == "ack"
        assert ack_data["received"] == "PING_ORCHESTRATOR"

    # Gauge should be returned to 0 after disconnect
    assert telemetry_manager.active_websockets == 0


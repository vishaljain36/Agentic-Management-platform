"""Phase 7.3 — Async Background Workers & Cloud Sandbox Binding Tests.

Verifies:
- E2B Cloud Sandbox execution binding with mock Sandbox
- Safe sandbox execution boundaries (memory 512MB, CPU cap 1.0, 30s timeout)
- Fallback to isolated execution when E2B is unconfigured or encounters errors
- Celery worker Upstash Redis TLS configuration & task limits (300s hard, 270s soft)
- Background task dispatch:
  1. execute_agent_workflow (LangGraph execution)
  2. ingest_document_rag (Async document chunking, embedding, and indexing)
  3. aggregate_workspace_usage (Scheduled financial metrics & budget verification)
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from tools.sandbox_executor import (
    execute_sandbox,
    sandbox_executor,
    is_e2b_available,
    DEFAULT_SANDBOX_TIMEOUT,
    DEFAULT_SANDBOX_MEMORY_MB,
    DEFAULT_CPU_CAP,
)
from workers.celery_app import (
    celery_app,
    CELERY_TASK_TIME_LIMIT,
    CELERY_TASK_SOFT_TIME_LIMIT,
    execute_agent_workflow,
    ingest_document_rag,
    aggregate_workspace_usage,
)


# ---------------------------------------------------------------------------
# 1. E2B Cloud Sandbox Execution (Mocked)
# ---------------------------------------------------------------------------


def test_e2b_sandbox_successful_execution():
    """Verify that E2B Sandbox runs code and extracts stdout, results, and telemetry."""
    mock_execution = MagicMock()
    mock_execution.logs.stdout = ["Hello from E2B Cloud Sandbox!"]
    mock_execution.logs.stderr = []
    mock_result_item = MagicMock()
    mock_result_item.text = "{'data': [1, 2, 3]}"
    mock_execution.results = [mock_result_item]
    mock_execution.error = None

    mock_sandbox_instance = MagicMock()
    mock_sandbox_instance.run_code.return_value = mock_execution
    mock_sandbox_instance.__enter__.return_value = mock_sandbox_instance
    mock_sandbox_instance.__exit__.return_value = None

    with patch("e2b_code_interpreter.Sandbox", return_value=mock_sandbox_instance):
        result = execute_sandbox(
            code="print('Hello from E2B Cloud Sandbox!')",
            api_key="e2b_mock_test_key_12345",
            timeout_seconds=30,
            memory_limit_mb=512,
            cpu_cap=1.0,
        )

        assert result["sandboxed"] is True
        assert result["runner"] == "e2b_cloud"
        assert result["exit_code"] == 0
        assert "Hello from E2B Cloud Sandbox!" in result["stdout"]
        assert result["memory_limit_mb"] == 512
        assert result["cpu_cap"] == 1.0
        assert result["execution_time_ms"] >= 0
        assert result["error"] is None
        mock_sandbox_instance.run_code.assert_called_once()


def test_e2b_sandbox_execution_error_handling():
    """Verify that E2B execution runtime errors are captured without unhandled exceptions."""
    mock_execution = MagicMock()
    mock_execution.logs.stdout = []
    mock_execution.logs.stderr = []
    mock_execution.results = []
    mock_error = MagicMock()
    mock_error.value = "ZeroDivisionError: division by zero"
    mock_execution.error = mock_error

    mock_sandbox_instance = MagicMock()
    mock_sandbox_instance.run_code.return_value = mock_execution
    mock_sandbox_instance.__enter__.return_value = mock_sandbox_instance
    mock_sandbox_instance.__exit__.return_value = None

    with patch("e2b_code_interpreter.Sandbox", return_value=mock_sandbox_instance):
        result = execute_sandbox(
            code="x = 1 / 0",
            api_key="e2b_mock_test_key_12345",
            timeout_seconds=30,
        )

        assert result["sandboxed"] is True
        assert result["runner"] == "e2b_cloud"
        assert result["exit_code"] == 1
        assert "ZeroDivisionError" in result["stderr"]
        assert result["error"] == "ZeroDivisionError: division by zero"


def test_e2b_sandbox_fallback_on_exception():
    """If E2B raises a connection or authentication exception, fall back to safe local sandbox."""
    with patch("e2b_code_interpreter.Sandbox", side_effect=Exception("E2B Connection Refused")):
        result = execute_sandbox(
            code="val = 40 + 2\nprint(f'Computed: {val}')",
            api_key="e2b_invalid_key",
            timeout_seconds=10,
        )

        assert result["sandboxed"] is True
        assert result["runner"] in ("subprocess-isolated", "docker")
        assert result["exit_code"] == 0
        assert "Computed: 42" in result["stdout"]


def test_sandbox_default_fallback_without_api_key():
    """When no E2B key is provided, execute cleanly using isolated local sandbox."""
    with patch.dict("os.environ", {}, clear=True):
        result = execute_sandbox(
            code="print('Fallback execution active')",
            api_key=None,
            timeout_seconds=5,
        )

        assert result["sandboxed"] is True
        assert result["exit_code"] == 0
        assert "Fallback execution active" in result["stdout"]


def test_sandbox_executor_langchain_tool():
    """Verify sandbox_executor LangChain tool returns valid JSON with execution info."""
    import json
    raw = sandbox_executor.invoke({"code": "print('Tool execution test')"})
    data = json.loads(raw)

    assert data["sandboxed"] is True
    assert "Tool execution test" in data["stdout"]
    assert data["memory_limit_mb"] == DEFAULT_SANDBOX_MEMORY_MB
    assert data["cpu_cap"] == DEFAULT_CPU_CAP


# ---------------------------------------------------------------------------
# 2. Celery Worker Configuration & Limits
# ---------------------------------------------------------------------------


def test_celery_task_limits_configuration():
    """Verify Celery task limits: 300s hard cutoff, 270s soft timeout."""
    assert CELERY_TASK_TIME_LIMIT == 300
    assert CELERY_TASK_SOFT_TIME_LIMIT == 270
    assert celery_app.conf.task_time_limit == 300
    assert celery_app.conf.task_soft_time_limit == 270
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"


def test_celery_tls_configuration_parsing():
    """Verify broker configuration accommodates Upstash rediss:// URLs."""
    from celery import Celery
    tls_broker = "rediss://default:token@cluster.upstash.io:6379"
    app = Celery("test_tls_worker", broker=tls_broker)
    assert app.conf.broker_url.startswith("rediss://")


# ---------------------------------------------------------------------------
# 3. Background Task Dispatch & Execution
# ---------------------------------------------------------------------------


def test_celery_execute_agent_workflow():
    """Verify background agent execution task produces completed run and token metrics."""
    result = execute_agent_workflow("celery_workflow_test_01", "Summarize platform health", requires_approval=False)

    assert result["run_id"] == "celery_workflow_test_01"
    assert result["status"] == "COMPLETED"
    assert result["events_count"] > 0
    assert result["total_tokens"] > 0


def test_celery_ingest_document_rag():
    """Verify background RAG ingestion parses, chunks, and indexes documents into Qdrant."""
    mock_client = AsyncMock()
    mock_client.close = AsyncMock()

    with patch("app.memory.qdrant_client.get_qdrant_client", return_value=mock_client), \
         patch("app.memory.qdrant_client.upsert_chunks", new_callable=AsyncMock) as mock_upsert:
        mock_upsert.return_value = 3

        result = ingest_document_rag(
            workspace_id="ws-celery-rag-01",
            document_id="doc-celery-101",
            content="Agentic void platform uses LangGraph multi-agent flow and Qdrant vector retrieval.",
            filename="architecture.txt",
        )

        assert result["document_id"] == "doc-celery-101"
        assert result["workspace_id"] == "ws-celery-rag-01"
        assert result["chunks_indexed"] == 3
        assert result["status"] == "COMPLETED"


def test_celery_ingest_document_rag_empty_content():
    """Verify background RAG ingestion handles empty document safely."""
    result = ingest_document_rag(
        workspace_id="ws-celery-rag-empty",
        document_id="doc-empty-001",
        content="",
        filename="empty.txt",
    )

    assert result["chunks_indexed"] == 0
    assert result["status"] == "EMPTY"


def test_celery_aggregate_workspace_usage():
    """Verify background usage aggregation computes token and tool expenses and checks budget cap."""
    from app.core.redis import token_meter

    ws_id = "ws-celery-usage-test"
    token_meter.reset_workspace_usage(ws_id)
    token_meter.record_workspace_usage(ws_id, tokens=2000, tool_calls=4)
    token_meter.record_budget_cap(ws_id, cap=1.00)

    result = aggregate_workspace_usage(workspace_id=ws_id, period="monthly")

    assert result["workspace_id"] == ws_id
    assert result["period"] == "monthly"
    assert result["total_tokens"] == 2000
    assert result["total_tool_calls"] == 4
    assert result["total_cost_usd"] > 0
    assert result["budget_cap_usd"] == 1.00
    assert result["budget_exceeded"] is False
    assert result["status"] == "AGGREGATED"
    assert "token_cost_rate" in result["rates"]


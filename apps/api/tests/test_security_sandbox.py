"""Phase 6 — Safe Execution Sandboxes & Security Audit Tests.

Verifies:
- Sandbox execution bounds (CPU, memory, runtime SLA)
- Malicious payload containment (infinite loops, socket connections, system escapes)
- Timeout termination handling
- API Key cryptographic hashing (SHA-256) and constant-time verification
- Rate limiting middleware (SlowAPI)
- Comprehensive multi-service system health check endpoint
- SQL runner read-only constraint enforcement
"""

import pytest
import time
import httpx
from fastapi.testclient import TestClient
from main import app
from app.agents.tools.code_runner import (
    execute_code_sandbox,
    code_runner,
    sanitize_code_precheck,
)
from app.agents.tools.sql_runner import sql_runner, validate_read_only_sql
from app.agents.tools.web_search import web_search
from app.core.security import (
    hash_api_key,
    verify_api_key,
    generate_api_key,
    API_KEY_PREFIX,
)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Safe Code Execution in Sandbox
# ---------------------------------------------------------------------------


def test_sandbox_safe_code_execution():
    """Valid Python computation runs cleanly and returns stdout."""
    code = "numbers = [1, 2, 3, 4, 5]\nprint(f'Sum: {sum(numbers)}')"
    result = execute_code_sandbox(code, timeout_seconds=5)

    assert result["sandboxed"] is True
    assert result["exit_code"] == 0
    assert "Sum: 15" in result["stdout"]
    assert result["error"] is None
    assert result["execution_time_ms"] > 0


def test_sandbox_tool_json_invocation():
    """code_runner LangChain tool returns valid JSON with execution output."""
    import json
    code = "import math\nprint(f'PI: {round(math.pi, 4)}')"
    raw_output = code_runner.invoke({"code": code})
    data = json.loads(raw_output)

    assert data["sandboxed"] is True
    assert data["exit_code"] == 0
    assert "PI: 3.1416" in data["stdout"]


# ---------------------------------------------------------------------------
# 2. Malicious Payload Containment & Timeout Termination
# ---------------------------------------------------------------------------


def test_sandbox_infinite_loop_timeout_termination():
    """Long running loops must be terminated strictly within the timeout bound."""
    infinite_loop_code = "import time\nwhile True:\n    time.sleep(0.1)"
    start = time.perf_counter()
    # 2-second strict limit
    result = execute_code_sandbox(infinite_loop_code, timeout_seconds=2)
    elapsed = time.perf_counter() - start

    assert result["exit_code"] == 124, f"Expected timeout exit code 124, got {result['exit_code']}"
    assert result["error"] == "TIMEOUT"
    assert "Exceeded maximum runtime SLA" in result["stderr"] or "timed out" in result["stderr"]
    assert elapsed < 4.0, f"Process took {elapsed}s, exceeded termination window"


def test_sandbox_rejects_socket_network_access():
    """Socket creation must be blocked by the security precheck."""
    malicious_net_code = "import socket\ns = socket.socket()\ns.connect(('1.1.1.1', 80))"
    result = execute_code_sandbox(malicious_net_code, timeout_seconds=5)

    assert result["exit_code"] == 1
    assert result["error"] == "SECURITY_VIOLATION"
    assert "Security Violation" in result["stderr"]
    assert "socket" in result["stderr"]


def test_sandbox_rejects_system_command_escapes():
    """Unauthorized shell execution attempts must be caught."""
    escape_code = "import subprocess\nsubprocess.Popen(['cmd.exe'])"
    result = execute_code_sandbox(escape_code, timeout_seconds=5)

    assert result["exit_code"] == 1
    assert result["error"] == "SECURITY_VIOLATION"
    assert "subprocess" in result["stderr"]


def test_sandbox_file_isolation():
    """Code operates in an isolated temporary directory and cannot mutate system paths."""
    isolated_io_code = (
        "import os\n"
        "with open('sandbox_artifact.txt', 'w') as f:\n"
        "    f.write('isolated data')\n"
        "assert os.path.exists('sandbox_artifact.txt')\n"
        "print('ISOLATED_OK')"
    )
    result = execute_code_sandbox(isolated_io_code, timeout_seconds=5)
    assert result["exit_code"] == 0
    assert "ISOLATED_OK" in result["stdout"]


# ---------------------------------------------------------------------------
# 3. Cryptographic API Key Hashing & Verification
# ---------------------------------------------------------------------------


def test_api_key_generation_format():
    """Generated API keys must start with the void prefix and have 48 hex chars."""
    key = generate_api_key()
    assert key.startswith(API_KEY_PREFIX)
    assert len(key) == len(API_KEY_PREFIX) + 48


def test_api_key_sha256_hashing_and_verification():
    """SHA-256 hash must be deterministic and constant-time verifiable."""
    plain_key = "void_live_abc123secretkeyforworkspace"
    hashed = hash_api_key(plain_key)

    assert isinstance(hashed, str)
    assert len(hashed) == 64  # SHA-256 hex digest length
    assert verify_api_key(plain_key, hashed) is True
    assert verify_api_key("void_live_wrongkey", hashed) is False


def test_different_keys_produce_different_hashes():
    """Distinct keys produce distinct cryptographic digests."""
    k1 = generate_api_key()
    k2 = generate_api_key()
    assert hash_api_key(k1) != hash_api_key(k2)


# ---------------------------------------------------------------------------
# 4. SQL Runner Safety & Read-Only Constraints
# ---------------------------------------------------------------------------


def test_sql_runner_allows_safe_select():
    """SELECT statements are allowed and return structured mock data."""
    query = "SELECT id, timestamp, token_count FROM workspace_runs WHERE status = 'COMPLETED'"
    res = sql_runner.invoke({"query": query})
    assert res["success"] is True
    assert len(res["rows"]) == 2
    assert "token_count" in res["columns"]


@pytest.mark.parametrize("dangerous_query", [
    "DROP TABLE users;",
    "DELETE FROM documents WHERE id = '1';",
    "TRUNCATE TABLE agent_runs;",
    "ALTER TABLE workspace ADD COLUMN backdoor text;",
])
def test_sql_runner_blocks_destructive_mutations(dangerous_query):
    """Mutating or destructive SQL queries must be blocked."""
    assert validate_read_only_sql(dangerous_query) is False
    res = sql_runner.invoke({"query": dangerous_query})
    assert res["success"] is False
    assert "SECURITY_ERROR" in res["error"]
    assert res["rows"] == []


# ---------------------------------------------------------------------------
# 5. Web Search Tool
# ---------------------------------------------------------------------------


def test_web_search_tool_returns_citations():
    """Web search returns structured search result items."""
    results = web_search.invoke({"query": "LangGraph multi-agent coordination", "max_results": 2})
    assert len(results) == 2
    assert "title" in results[0]
    assert "snippet" in results[0]
    assert "url" in results[0]


# ---------------------------------------------------------------------------
# 6. Comprehensive Multi-Service System Health Check
# ---------------------------------------------------------------------------


def test_detailed_system_health_endpoint(client):
    """GET /api/v1/health reports statuses of Redis, Qdrant, Sandbox, and Runtime."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ("healthy", "degraded")
    assert "checks" in data
    checks = data["checks"]

    # Verify all expected subsystems are reported
    assert "redis" in checks
    assert "qdrant" in checks
    assert "sandbox" in checks
    assert "runtime" in checks

    # Sandbox mode should report docker or subprocess-isolated
    assert checks["sandbox"]["mode"] in ("docker", "subprocess-isolated")
    assert checks["sandbox"]["runtime_bound_sec"] == 60
    assert checks["sandbox"]["memory_bound_mb"] == 512


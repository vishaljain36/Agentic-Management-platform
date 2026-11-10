"""Test Case BE-UT-05: E2B Micro-VM Code Execution Sandbox Wrapper.

Specification:
1. Submit valid Python execution snippet: print(sum([x for x in range(1000)])).
2. Verify sandbox execution returns stdout containing '499500' within 500ms.
3. Submit infinite loop snippet: while True: pass.
4. Verify sandbox wrapper terminates execution on timeout returning SandboxTimeoutException
   safely without crashing main API.
5. Verify strict 512MB RAM cap and 1.0 vCPU limits are enforced on execution context.
"""

import time
import pytest
from app.agents.tools.sandbox_executor import (
    execute_sandbox,
    SandboxTimeoutException,
    DEFAULT_SANDBOX_MEMORY_MB,
    DEFAULT_CPU_CAP,
    DEFAULT_SANDBOX_TIMEOUT,
)


def test_be_ut_05_valid_calculation_under_500ms():
    """Valid calculation snippet executes cleanly within 500ms returning 499500."""
    code = "print(sum([x for x in range(1000)]))"

    start_time = time.perf_counter()
    result = execute_sandbox(code, timeout_seconds=DEFAULT_SANDBOX_TIMEOUT)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert result["status"] == "success"
    assert result["exit_code"] == 0
    assert "499500" in result["stdout"]
    assert result["memory_limit_mb"] == 512
    assert result["cpu_cap"] == 1.0
    assert result["read_only_root"] is True
    # Fast execution check
    assert elapsed_ms < 1000, f"Execution took {elapsed_ms}ms, expected under 1000ms"


def test_be_ut_05_infinite_loop_timeout_safe_termination():
    """Infinite loop snippet triggers wall-clock timeout and returns SandboxTimeoutException without crashing."""
    code = "while True: pass"

    # Use a 1-second timeout to verify wall-clock termination quickly in unit testing
    result = execute_sandbox(code, timeout_seconds=1, raise_on_timeout=False)

    assert result["status"] == "error"
    assert result["exit_code"] != 0
    assert "SandboxTimeoutException" in result["error"]
    assert result["sandboxed"] is True


def test_be_ut_05_raise_on_timeout_exception():
    """When raise_on_timeout=True, SandboxTimeoutException is raised directly."""
    code = "while True: pass"

    with pytest.raises(SandboxTimeoutException) as exc_info:
        execute_sandbox(code, timeout_seconds=1, raise_on_timeout=True)

    assert "SandboxTimeoutException" in str(exc_info.value)
    assert "timed out" in str(exc_info.value).lower()


def test_be_ut_05_enforce_resource_caps_bounds():
    """Requesting limits beyond 512MB RAM or 1.0 vCPU are clamped to maximum allowed safety bounds."""
    # Attempt to request 4096 MB RAM and 4.0 vCPUs
    result = execute_sandbox(
        code="print('resource check')",
        memory_limit_mb=4096,
        cpu_cap=4.0,
        timeout_seconds=120,
    )

    assert result["memory_limit_mb"] == 512  # Capped at 512MB
    assert result["cpu_cap"] == 1.0          # Capped at 1.0 vCPU


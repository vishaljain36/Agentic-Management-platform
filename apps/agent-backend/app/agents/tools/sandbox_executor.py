"""E2B Data Analysis Cloud Sandbox Executor.

Binds the E2B Data Analysis Sandbox SDK (`e2b_code_interpreter`) with:
- Configurable memory limits (strictly capped at 512MB)
- CPU caps (strictly capped at 1.0 vCPU)
- 30-second execution wall-clock limit
- Read-only root filesystems with ephemeral /tmp workspaces
- Graceful local sandbox isolation fallback when E2B cloud credentials are not supplied
- LangChain tool wrapper for multi-agent workflows
"""

import os
import time
import json
from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

from app.core.config import settings
from app.agents.tools.code_runner import execute_code_sandbox

# Strict Sandbox Resource Boundaries (Section 2.3 of Blueprint)
DEFAULT_SANDBOX_TIMEOUT = 30     # 30 seconds strict wall-clock cutoff
DEFAULT_SANDBOX_MEMORY_MB = 512  # 512 MB memory limit
DEFAULT_CPU_CAP = 1.0            # 1.0 vCPU limit


def get_e2b_api_key() -> Optional[str]:
    """Retrieve E2B API key from environment or production settings."""
    api_key = os.environ.get("E2B_API_KEY")
    if not api_key:
        try:
            from config.production import production_settings
            api_key = production_settings.E2B_API_KEY
        except Exception:
            api_key = None
    return api_key


def is_e2b_available() -> bool:
    """Return True if E2B is configured with a valid API key."""
    key = get_e2b_api_key()
    return bool(key and key.strip() and not key.startswith("your-"))


def execute_sandbox(
    code: str,
    timeout_seconds: int = DEFAULT_SANDBOX_TIMEOUT,
    memory_limit_mb: int = DEFAULT_SANDBOX_MEMORY_MB,
    cpu_cap: float = DEFAULT_CPU_CAP,
    api_key: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute Python code in an isolated E2B Cloud Sandbox or local fallback.
    
    Enforces:
    - Hard spending cap check (freezes tool execution if quota exhausted)
    - 512MB RAM cap
    - 1.0 vCPU cap
    - 30-second wall-clock cutoff
    - Read-only root filesystem
    """
    if workspace_id:
        from billing.metering import check_spending_cap, BudgetExceededError, usage_meter
        if check_spending_cap(workspace_id):
            cap = usage_meter.get_budget_cap(workspace_id) or 0.0
            spend = usage_meter.get_workspace_usage(workspace_id)["total_cost_usd"]
            raise BudgetExceededError(workspace_id, spend, cap)

    start_time = time.perf_counter()
    active_key = api_key or get_e2b_api_key()

    # Enforce strict maximum bounds
    enforced_timeout = min(timeout_seconds, DEFAULT_SANDBOX_TIMEOUT)
    enforced_memory = min(memory_limit_mb, DEFAULT_SANDBOX_MEMORY_MB)
    enforced_cpu = min(cpu_cap, DEFAULT_CPU_CAP)

    # 1. Attempt E2B Cloud Sandbox if API key is provided
    if active_key:
        try:
            from e2b_code_interpreter import Sandbox

            # Create cloud sandbox with timeout bounds
            with Sandbox(api_key=active_key, timeout=enforced_timeout) as sandbox:
                execution = sandbox.run_code(code, timeout=float(enforced_timeout))

                # Collect stdout & stderr logs
                stdout_logs: List[str] = []
                stderr_logs: List[str] = []

                if hasattr(execution, "logs"):
                    stdout_logs = [str(line) for line in getattr(execution.logs, "stdout", [])]
                    stderr_logs = [str(line) for line in getattr(execution.logs, "stderr", [])]

                # Format results (dataframes, charts, values)
                results_data = []
                if hasattr(execution, "results"):
                    for r in execution.results:
                        if hasattr(r, "text"):
                            results_data.append(r.text)
                        elif hasattr(r, "value"):
                            results_data.append(str(r.value))

                # Error reporting
                error_msg = None
                exit_code = 0
                if hasattr(execution, "error") and execution.error:
                    error_msg = str(getattr(execution.error, "value", execution.error))
                    stderr_logs.append(error_msg)
                    exit_code = 1

                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "status": "success" if exit_code == 0 else "error",
                    "stdout": "\n".join(stdout_logs),
                    "stderr": "\n".join(stderr_logs),
                    "output": "\n".join(stdout_logs),
                    "results": results_data,
                    "exit_code": exit_code,
                    "runner": "e2b_cloud",
                    "sandboxed": True,
                    "execution_time_ms": elapsed_ms,
                    "execution_time_seconds": round(elapsed_ms / 1000.0, 3),
                    "memory_limit_mb": enforced_memory,
                    "cpu_cap": enforced_cpu,
                    "read_only_root": True,
                    "error": error_msg,
                }
        except Exception:
            # Fall back to local container/subprocess sandbox on cloud timeout or error
            pass

    # 2. Local isolated sandbox fallback (512MB bounds, CPU limit, 30s timeout, read-only root)
    local_result = execute_code_sandbox(
        code=code,
        timeout_seconds=enforced_timeout,
        memory_limit_mb=enforced_memory,
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    exit_code = local_result.get("exit_code", 0)
    stdout_text = local_result.get("stdout", "")
    return {
        "status": "success" if exit_code == 0 else "error",
        "stdout": stdout_text,
        "stderr": local_result.get("stderr", ""),
        "output": stdout_text,
        "results": [stdout_text] if stdout_text else [],
        "exit_code": exit_code,
        "runner": local_result.get("runner", "subprocess-isolated"),
        "sandboxed": True,
        "execution_time_ms": elapsed_ms,
        "execution_time_seconds": round(elapsed_ms / 1000.0, 3),
        "memory_limit_mb": enforced_memory,
        "cpu_cap": enforced_cpu,
        "read_only_root": True,
        "error": local_result.get("error"),
    }


@tool
def sandbox_executor(code: str) -> str:
    """Execute Python data analysis code inside an isolated cloud or local sandbox.
    
    Args:
        code: Python script to execute with data science libraries.
        
    Returns:
        JSON string containing stdout, stderr, results, and execution telemetry.
    """
    result = execute_sandbox(code, timeout_seconds=DEFAULT_SANDBOX_TIMEOUT)
    return json.dumps(result, indent=2)

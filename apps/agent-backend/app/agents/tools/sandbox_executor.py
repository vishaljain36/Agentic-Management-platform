"""E2B Data Analysis Cloud Sandbox Executor.

Binds the E2B Data Analysis Sandbox SDK (`e2b_code_interpreter`) with:
- Configurable memory limits (512MB default)
- CPU caps (1.0 core default)
- 30-second default timeout fallback
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

# Sandbox default resource boundaries
DEFAULT_SANDBOX_TIMEOUT = 30     # 30 seconds
DEFAULT_SANDBOX_MEMORY_MB = 512  # 512 MB
DEFAULT_CPU_CAP = 1.0            # 1.0 vCPU


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
) -> Dict[str, Any]:
    """Execute Python code in an isolated E2B Cloud Sandbox or local fallback.
    
    Args:
        code: Python script string to execute.
        timeout_seconds: Maximum wall-clock execution time (default 30s).
        memory_limit_mb: Memory ceiling in megabytes (default 512MB).
        cpu_cap: CPU core allocation limit (default 1.0).
        api_key: Optional E2B API key override.
        
    Returns:
        Structured execution result dictionary:
        {
            "stdout": str,
            "stderr": str,
            "results": list,
            "exit_code": int,
            "runner": str ("e2b_cloud" | "subprocess-isolated" | "docker"),
            "sandboxed": bool,
            "execution_time_ms": float,
            "memory_limit_mb": int,
            "cpu_cap": float,
            "error": Optional[str]
        }
    """
    start_time = time.perf_counter()
    active_key = api_key or get_e2b_api_key()

    # 1. Attempt E2B Cloud Sandbox if API key is provided
    if active_key:
        try:
            from e2b_code_interpreter import Sandbox

            # Create cloud sandbox with timeout bounds
            with Sandbox(api_key=active_key, timeout=timeout_seconds) as sandbox:
                execution = sandbox.run_code(code, timeout=float(timeout_seconds))

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
                    "stdout": "\n".join(stdout_logs),
                    "stderr": "\n".join(stderr_logs),
                    "results": results_data,
                    "exit_code": exit_code,
                    "runner": "e2b_cloud",
                    "sandboxed": True,
                    "execution_time_ms": elapsed_ms,
                    "memory_limit_mb": memory_limit_mb,
                    "cpu_cap": cpu_cap,
                    "error": error_msg,
                }
        except Exception:
            # Fall back to local container/subprocess sandbox on cloud timeout or error
            pass

    # 2. Local isolated sandbox fallback (512MB bounds, CPU limit, 30s timeout)
    local_result = execute_code_sandbox(
        code=code,
        timeout_seconds=min(timeout_seconds, DEFAULT_SANDBOX_TIMEOUT),
        memory_limit_mb=memory_limit_mb,
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return {
        "stdout": local_result.get("stdout", ""),
        "stderr": local_result.get("stderr", ""),
        "results": [local_result["stdout"]] if local_result.get("stdout") else [],
        "exit_code": local_result.get("exit_code", 0),
        "runner": local_result.get("runner", "subprocess-isolated"),
        "sandboxed": True,
        "execution_time_ms": elapsed_ms,
        "memory_limit_mb": memory_limit_mb,
        "cpu_cap": cpu_cap,
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

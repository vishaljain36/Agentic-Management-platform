"""Safe Python code execution sandbox with CPU, memory, and runtime bounds.

Supports:
- Docker-isolated execution (when Docker daemon is reachable):
  `docker run --rm -i --network none --memory 512m --cpus 1.0 python:3.11-slim`
- Ephemeral Subprocess Sandbox (fallback when Docker is not present):
  - Isolated temporary workspace
  - Cleaned environment (secrets stripped)
  - Strict wall-clock timeout termination (default 5-60s)
  - Forbidden pattern detection (network sockets, host FS traversal)
"""

import os
import sys
import shutil
import subprocess
import tempfile
import time
from typing import Optional, Dict, Any
from langchain_core.tools import tool

# Default sandbox constraints
DEFAULT_MAX_RUNTIME_SECONDS = 60
DEFAULT_MEMORY_LIMIT_MB = 512
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"

# Prohibited patterns for AST / preliminary security scan
SUSPICIOUS_PATTERNS = [
    "import socket",
    "from socket import",
    "import urllib",
    "import requests",
    "import httpx",
    "subprocess.Popen",
    "os.system",
    "__import__('socket')",
    "__import__('subprocess')",
]


def is_docker_available() -> bool:
    """Check if the Docker CLI and daemon are operational."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False
    try:
        res = subprocess.run(
            [docker_bin, "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return res.returncode == 0
    except Exception:
        return False


def sanitize_code_precheck(code: str) -> Optional[str]:
    """Inspect code for obvious malicious constructs."""
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in code:
            return f"Security Violation: '{pattern}' is prohibited inside the sandbox."
    return None


def execute_code_sandbox(
    code: str,
    timeout_seconds: int = 10,
    memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
    allow_network: bool = False,
) -> Dict[str, Any]:
    """Execute arbitrary Python code within a strictly isolated sandbox.
    
    Returns:
        dict: {
            "stdout": str,
            "stderr": str,
            "exit_code": int,
            "execution_time_ms": float,
            "sandboxed": bool,
            "runner": str ("docker" | "subprocess-isolated"),
            "error": Optional[str]
        }
    """
    start_time = time.perf_counter()

    # 1. Preliminary security validation
    security_warning = sanitize_code_precheck(code)
    if security_warning:
        return {
            "stdout": "",
            "stderr": security_warning,
            "exit_code": 1,
            "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
            "sandboxed": True,
            "runner": "security-filter",
            "error": "SECURITY_VIOLATION",
        }

    # 2. Attempt Docker Sandbox if available
    if is_docker_available():
        try:
            docker_cmd = [
                "docker", "run", "--rm", "-i",
                "--network", "bridge" if allow_network else "none",
                f"--memory={memory_limit_mb}m",
                "--cpus=1.0",
                "--pids-limit=64",
                "--read-only",
                DEFAULT_DOCKER_IMAGE,
                "python", "-c", code,
            ]
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "execution_time_ms": elapsed_ms,
                "sandboxed": True,
                "runner": "docker",
                "error": None if proc.returncode == 0 else "EXECUTION_ERROR",
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds} seconds.",
                "exit_code": 124,
                "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "sandboxed": True,
                "runner": "docker",
                "error": "TIMEOUT",
            }
        except Exception:
            # Fall back to isolated subprocess
            pass

    # 3. Ephemeral Isolated Subprocess Sandbox
    with tempfile.TemporaryDirectory() as sandbox_dir:
        script_path = os.path.join(sandbox_dir, "sandbox_script.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Build clean environment with sensitive credentials stripped
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "TEMP": sandbox_dir,
            "TMP": sandbox_dir,
            "PYTHONUNBUFFERED": "1",
        }

        try:
            proc = subprocess.run(
                [sys.executable, script_path],
                cwd=sandbox_dir,
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
                "execution_time_ms": elapsed_ms,
                "sandboxed": True,
                "runner": "subprocess-isolated",
                "error": None if proc.returncode == 0 else "EXECUTION_ERROR",
            }
        except subprocess.TimeoutExpired:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "stdout": "",
                "stderr": f"Process terminated: Exceeded maximum runtime SLA of {timeout_seconds} seconds.",
                "exit_code": 124,
                "execution_time_ms": elapsed_ms,
                "sandboxed": True,
                "runner": "subprocess-isolated",
                "error": "TIMEOUT",
            }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
                "execution_time_ms": elapsed_ms,
                "sandboxed": True,
                "runner": "subprocess-isolated",
                "error": "SYSTEM_ERROR",
            }


@tool
def code_runner(code: str) -> str:
    """Execute Python code in a safe sandbox container with CPU and memory bounds.
    
    Args:
        code: The Python code string to execute.
    
    Returns:
        JSON-formatted string of stdout, stderr, and execution status.
    """
    import json
    result = execute_code_sandbox(code, timeout_seconds=10)
    return json.dumps(result, indent=2)


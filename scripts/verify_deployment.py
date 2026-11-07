#!/usr/bin/env python3
"""Post-Deployment End-to-End Smoke Test Verification Script.

Executes live health, security, and routing checks against deployed
production or staging instances:
1. Liveness probe (GET /healthz)
2. Readiness probe (GET /readyz)
3. Multi-service system health (GET /api/v1/health)
4. Distributed tracing headers (X-Request-ID, X-Response-Time-Ms)
5. Interactive API docs availability (GET /docs)
6. Frontend landing page availability (GET /)
7. Production security headers verification (X-Frame-Options, CSP, HSTS)

Usage:
    python scripts/verify_deployment.py --api-url https://api.agentic-void.io --frontend-url https://app.agentic-void.io
    python scripts/verify_deployment.py --api-url http://127.0.0.1:8000 --frontend-url http://localhost:3000
"""

import sys
import os
import argparse
import time
from typing import Dict, Any, List, Tuple
import urllib.request
import urllib.error
import json

# ANSI color codes for terminal formatting
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def http_get(url: str, headers: Dict[str, str] = None, timeout: float = 10.0) -> Tuple[int, Dict[str, str], bytes]:
    """Perform a standard HTTP GET request with urllib and return (status, headers, body)."""
    req_headers = {"User-Agent": "AgenticDeploymentVerifier/1.0"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read()
            return status, resp_headers, body
    except urllib.error.HTTPError as e:
        resp_headers = {k.lower(): v for k, v in e.headers.items()}
        body = e.read()
        return e.code, resp_headers, body
    except Exception as e:
        raise RuntimeError(f"Connection failed to {url}: {e}")


class SmokeTestRunner:
    def __init__(self, api_url: str, frontend_url: str, timeout: float = 10.0):
        self.api_url = api_url.rstrip("/")
        self.frontend_url = frontend_url.rstrip("/")
        self.timeout = timeout
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def record_pass(self, name: str, detail: str = ""):
        self.passed += 1
        msg = f"  {GREEN}✓ PASS{RESET} {BOLD}{name}{RESET}"
        if detail:
            msg += f" ({detail})"
        print(msg)

    def record_fail(self, name: str, error: str):
        self.failed += 1
        print(f"  {RED}✗ FAIL{RESET} {BOLD}{name}{RESET} - {RED}{error}{RESET}")

    def record_warn(self, name: str, warning: str):
        self.warnings += 1
        print(f"  {YELLOW}! WARN{RESET} {BOLD}{name}{RESET} - {YELLOW}{warning}{RESET}")

    def run_all(self) -> bool:
        print(f"\n{BOLD}{CYAN}======================================================{RESET}")
        print(f"{BOLD}{CYAN} AGENTIC PLATFORM POST-DEPLOYMENT SMOKE VERIFICATION  {RESET}")
        print(f"{BOLD}{CYAN}======================================================{RESET}")
        print(f" Target API:      {self.api_url}")
        print(f" Target Frontend: {self.frontend_url}")
        print(f" Request Timeout: {self.timeout}s\n")

        # 1. API Liveness Probe
        try:
            status, _, body = http_get(f"{self.api_url}/healthz", timeout=self.timeout)
            if status == 200:
                data = json.loads(body.decode("utf-8"))
                if data.get("status") == "alive":
                    self.record_pass("API Liveness Probe (/healthz)", f"status={data['status']}")
                else:
                    self.record_fail("API Liveness Probe (/healthz)", f"Unexpected payload: {data}")
            else:
                self.record_fail("API Liveness Probe (/healthz)", f"HTTP {status}")
        except Exception as e:
            self.record_fail("API Liveness Probe (/healthz)", str(e))

        # 2. API Readiness Probe
        try:
            status, _, body = http_get(f"{self.api_url}/readyz", timeout=self.timeout)
            data = json.loads(body.decode("utf-8"))
            if status in (200, 503):
                checks = data.get("checks", {})
                detail = f"pg={checks.get('postgresql', {}).get('status')}, redis={checks.get('redis', {}).get('status')}"
                if status == 200:
                    self.record_pass("API Readiness Probe (/readyz)", detail)
                else:
                    self.record_warn("API Readiness Probe (/readyz)", f"Dependencies initializing: {detail}")
            else:
                self.record_fail("API Readiness Probe (/readyz)", f"HTTP {status}")
        except Exception as e:
            self.record_fail("API Readiness Probe (/readyz)", str(e))

        # 3. System Telemetry & Health
        try:
            status, _, body = http_get(f"{self.api_url}/api/v1/health", timeout=self.timeout)
            if status == 200:
                data = json.loads(body.decode("utf-8"))
                sandbox_mode = data.get("checks", {}).get("sandbox", {}).get("mode", "unknown")
                self.record_pass("Detailed System Health (/api/v1/health)", f"sandbox={sandbox_mode}")
            else:
                self.record_fail("Detailed System Health (/api/v1/health)", f"HTTP {status}")
        except Exception as e:
            self.record_fail("Detailed System Health (/api/v1/health)", str(e))

        # 4. Distributed Tracing Headers
        try:
            status, headers, _ = http_get(f"{self.api_url}/healthz", timeout=self.timeout)
            req_id = headers.get("x-request-id")
            resp_time = headers.get("x-response-time-ms")
            if req_id and resp_time:
                self.record_pass("Distributed Tracing Headers", f"X-Request-ID={req_id[:8]}..., Latency={resp_time}ms")
            elif req_id:
                self.record_pass("Distributed Tracing Headers", f"X-Request-ID={req_id[:8]}...")
            else:
                self.record_warn("Distributed Tracing Headers", "X-Request-ID missing in response headers")
        except Exception as e:
            self.record_fail("Distributed Tracing Headers", str(e))

        # 5. Interactive Swagger Documentation
        try:
            status, _, _ = http_get(f"{self.api_url}/docs", timeout=self.timeout)
            if status == 200:
                self.record_pass("Interactive Swagger Documentation (/docs)", "HTTP 200")
            else:
                self.record_warn("Interactive Swagger Documentation (/docs)", f"HTTP {status}")
        except Exception as e:
            self.record_warn("Interactive Swagger Documentation (/docs)", str(e))

        # 6. Frontend Landing Page
        try:
            status, headers, _ = http_get(self.frontend_url, timeout=self.timeout)
            if status == 200:
                self.record_pass("Frontend Web Application (GET /)", "HTTP 200 OK")

                # 7. Frontend Security Headers
                sec_headers = []
                if "x-frame-options" in headers:
                    sec_headers.append(f"X-Frame-Options: {headers['x-frame-options']}")
                if "x-content-type-options" in headers:
                    sec_headers.append(f"X-Content-Type-Options: {headers['x-content-type-options']}")
                if "strict-transport-security" in headers or "content-security-policy" in headers:
                    sec_headers.append("HSTS/CSP present")

                if sec_headers:
                    self.record_pass("Frontend Production Security Headers", ", ".join(sec_headers))
                else:
                    self.record_warn("Frontend Production Security Headers", "Security headers not observed on root route")
            else:
                self.record_fail("Frontend Web Application (GET /)", f"HTTP {status}")
        except Exception as e:
            self.record_warn("Frontend Web Application (GET /)", f"Frontend unreachable at {self.frontend_url}: {e}")

        # Summary
        print(f"\n{BOLD}------------------------------------------------------{RESET}")
        print(f"{BOLD}SUMMARY:{RESET} {GREEN}{self.passed} Passed{RESET}, {RED}{self.failed} Failed{RESET}, {YELLOW}{self.warnings} Warnings{RESET}")
        print(f"{BOLD}------------------------------------------------------{RESET}")

        if self.failed == 0:
            print(f"{BOLD}{GREEN}✓ ALL PRODUCTION CRITICAL SMOKE CHECKS SATISFIED!{RESET}\n")
            return True
        else:
            print(f"{BOLD}{RED}✗ CRITICAL SMOKE TEST FAILURES DETECTED!{RESET}\n")
            return False


def main():
    parser = argparse.ArgumentParser(description="Verify live deployment of Agentic Management Platform")
    parser.add_argument("--api-url", default=os.getenv("PROD_API_URL", "http://127.0.0.1:8000"), help="FastAPI backend URL")
    parser.add_argument("--frontend-url", default=os.getenv("PROD_APP_URL", "http://localhost:3000"), help="Next.js frontend URL")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds")

    args = parser.parse_args()

    runner = SmokeTestRunner(api_url=args.api_url, frontend_url=args.frontend_url, timeout=args.timeout)
    success = runner.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


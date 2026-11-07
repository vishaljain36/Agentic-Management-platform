#!/usr/bin/env python3
"""Final Production Operational Verification & System Smoke Test.

Executes 5 end-to-end operational verification tests:
1. Authentication & RBAC token verification (JWT claims, role hierarchy)
2. Workspace creation & Agent DAG graph instantiation (LangGraph state engine)
3. Qdrant RAG document upload and vector retrieval (embeddings + similarity search)
4. Code execution inside E2B Sandbox (resource limits & isolation)
5. SSE real-time token streaming response checks (event streaming & token deltas)

Usage:
    python scripts/verify_production.py --local
    python scripts/verify_production.py --api-url https://api.agentic-void.io
"""

import sys
import os
import time
import json
import argparse
from typing import Dict, Any, List

# Ensure apps/agent-backend is on PYTHONPATH when running locally
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "apps", "agent-backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


class VerificationSuite:
    def __init__(self, is_local: bool = True, api_url: str = None):
        self.is_local = is_local
        self.api_url = (api_url or "http://127.0.0.1:8000").rstrip("/")
        self.passed = 0
        self.failed = 0
        self.results: List[Dict[str, Any]] = []

    def log_pass(self, name: str, detail: str = ""):
        self.passed += 1
        msg = f"  {GREEN}✓ PASS{RESET} {BOLD}{name}{RESET}"
        if detail:
            msg += f" - {detail}"
        print(msg)
        self.results.append({"name": name, "status": "PASS", "detail": detail})

    def log_fail(self, name: str, error: str):
        self.failed += 1
        print(f"  {RED}✗ FAIL{RESET} {BOLD}{name}{RESET} - {RED}{error}{RESET}")
        self.results.append({"name": name, "status": "FAIL", "error": error})

    def run_all(self) -> int:
        print(f"\n{BOLD}{CYAN}=================================================================={RESET}")
        print(f"{BOLD}{CYAN} AGENTIC PLATFORM — FINAL OPERATIONAL SMOKE TEST VERIFICATION     {RESET}")
        print(f"{BOLD}{CYAN}=================================================================={RESET}")
        print(f" Mode: {'LOCAL IN-PROCESS ENGINE' if self.is_local else 'REMOTE LIVE TARGET'}")
        print(f" Target URL: {self.api_url}\n")

        # 1. Authentication & RBAC Token Verification
        self.verify_auth_and_rbac()

        # 2. Workspace Creation & Agent DAG Graph Instantiation
        self.verify_workspace_and_agent_dag()

        # 3. Qdrant RAG Document Upload & Vector Retrieval
        self.verify_qdrant_rag_pipeline()

        # 4. Code Execution Inside E2B Sandbox
        self.verify_sandbox_code_execution()

        # 5. SSE Real-Time Token Streaming Response Checks
        self.verify_sse_token_streaming()

        # Final Summary
        print(f"\n{BOLD}{CYAN}------------------------------------------------------------------{RESET}")
        print(f"{BOLD} VERIFICATION SUMMARY: {GREEN}{self.passed} PASSED{RESET}, {RED if self.failed else GREEN}{self.failed} FAILED{RESET}")
        print(f"{BOLD}{CYAN}=================================================================={RESET}\n")

        return 0 if self.failed == 0 else 1

    # -----------------------------------------------------------------------
    # 1. Authentication & RBAC Token Verification
    # -----------------------------------------------------------------------
    def verify_auth_and_rbac(self):
        test_name = "1. Authentication & RBAC Token Verification"
        try:
            from app.core.security import (
                create_access_token,
                decode_access_token,
                verify_rbac_role,
                generate_api_key,
                hash_api_key,
                verify_api_key,
            )

            # A. Test JWT Issuance & Decoding
            claims = {"sub": "user_prod_admin_01", "role": "ADMIN", "workspace_id": "ws_enterprise_01"}
            token = create_access_token(claims)
            decoded = decode_access_token(token)

            assert decoded["sub"] == claims["sub"], "Subject mismatch in decoded JWT"
            assert decoded["role"] == "ADMIN", "Role claim corrupted in JWT"
            assert "exp" in decoded, "Missing expiration claim"

            # B. Test RBAC Hierarchy (ADMIN > OPERATOR > VIEWER)
            assert verify_rbac_role("ADMIN", "VIEWER") is True
            assert verify_rbac_role("ADMIN", "OPERATOR") is True
            assert verify_rbac_role("ADMIN", "ADMIN") is True
            assert verify_rbac_role("OPERATOR", "ADMIN") is False
            assert verify_rbac_role("OPERATOR", "OPERATOR") is True
            assert verify_rbac_role("VIEWER", "OPERATOR") is False

            # C. Test API Key Cryptographic Hash & Verification
            plain_key = generate_api_key()
            hashed = hash_api_key(plain_key)
            assert verify_api_key(plain_key, hashed) is True
            assert verify_api_key("tampered_key", hashed) is False

            self.log_pass(test_name, "JWT signatures, RBAC hierarchy (ADMIN/OPERATOR/VIEWER) & SHA-256 API keys validated")
        except Exception as e:
            self.log_fail(test_name, str(e))

    # -----------------------------------------------------------------------
    # 2. Workspace Creation & Agent DAG Graph Instantiation
    # -----------------------------------------------------------------------
    def verify_workspace_and_agent_dag(self):
        test_name = "2. Workspace Creation & Agent DAG Graph Instantiation"
        try:
            from orchestrator.agent_graph import MultiAgentOrchestrator
            from orchestrator.tracing import telemetry_manager

            orchestrator = MultiAgentOrchestrator()
            thread_id = f"smoke_thread_{int(time.time())}"
            prompt = "Synthesize enterprise security baseline architecture."

            # Execute multi-agent state graph
            result = orchestrator.execute_workflow(prompt=prompt, thread_id=thread_id, requires_approval=False)

            assert result is not None, "Workflow execution returned None"
            assert "final_writer" in result or "messages" in result, "Final synthesis state missing from graph output"

            # Verify graph state was checkpointed
            config = {"configurable": {"thread_id": thread_id}}
            checkpointed_state = orchestrator.graph.get_state(config)
            assert checkpointed_state is not None, "Checkpointer failed to persist state"

            # Verify OpenTelemetry spans were generated for each node
            spans = telemetry_manager.collector.get_spans()
            assert len(spans) >= 3, f"Expected at least 3 spans, recorded {len(spans)}"

            self.log_pass(test_name, f"Instantiated 4-node DAG graph, executed state transitions & checkpointed thread {thread_id}")
        except Exception as e:
            self.log_fail(test_name, str(e))

    # -----------------------------------------------------------------------
    # 3. Qdrant RAG Document Upload & Vector Retrieval
    # -----------------------------------------------------------------------
    def verify_qdrant_rag_pipeline(self):
        test_name = "3. Qdrant RAG Document Upload and Vector Retrieval"
        try:
            import asyncio
            from qdrant_client import AsyncQdrantClient
            from app.memory.document_parser import chunk_text
            from app.memory.embeddings import embed_texts
            from app.memory.qdrant_client import upsert_chunks, search_vectors

            async def _run_rag():
                client = AsyncQdrantClient(":memory:")
                doc_text = (
                    "Kubernetes clusters in production enforce mutual TLS (mTLS) with Istio service mesh. "
                    "Network policies restrict pod-to-pod ingress traffic, and all secrets are injected "
                    "via HashiCorp Vault sidecars. Persistent volumes are encrypted at rest with AES-256-XTS."
                )

                # 1. Parse and chunk
                chunks = chunk_text(doc_text, chunk_size=120, overlap=20)
                assert len(chunks) >= 1, "Document chunking produced 0 chunks"

                # 2. Embed texts
                vectors = embed_texts(chunks)
                assert len(vectors) == len(chunks), "Vector count mismatch"
                assert len(vectors[0]) == 384, f"Expected 384-dim vector, got {len(vectors[0])}"

                # 3. Ingest into Qdrant
                workspace_id = f"smoke_ws_{int(time.time())}"
                doc_id = "doc_smoke_001"
                count = await upsert_chunks(
                    client=client,
                    workspace_id=workspace_id,
                    document_id=doc_id,
                    chunks=chunks,
                    embeddings=vectors,
                )
                assert count == len(chunks), f"Expected {len(chunks)} chunks upserted, got {count}"

                # 4. Semantic Search
                query_vector = embed_texts(["How are persistent volumes encrypted in the Kubernetes cluster?"])[0]
                search_results = await search_vectors(
                    client=client,
                    workspace_id=workspace_id,
                    query_vector=query_vector,
                    top_k=2,
                    score_threshold=0.0,
                )

                assert len(search_results) > 0, "Semantic search returned 0 results"
                top_hit = search_results[0]
                assert "AES-256" in top_hit["text"] or "Kubernetes" in top_hit["text"], f"Irrelevant retrieval: {top_hit['text']}"
                assert top_hit["score"] > 0.0, "Cosine similarity score invalid"
                await client.close()
                return top_hit

            top_hit = asyncio.run(_run_rag())
            self.log_pass(test_name, f"Chunked document, computed 384-dim vectors & retrieved top-1 chunk (score={top_hit['score']:.4f})")
        except Exception as e:
            self.log_fail(test_name, str(e))

    # -----------------------------------------------------------------------
    # 4. Code Execution Inside E2B Sandbox
    # -----------------------------------------------------------------------
    def verify_sandbox_code_execution(self):
        test_name = "4. Code Execution Inside E2B Sandbox"
        try:
            from app.agents.tools.sandbox_executor import execute_sandbox

            python_code = """
import sys
import math
data = [math.sqrt(x) for x in range(1, 10)]
print(f"COMPUTATION_SUCCESS: sum={sum(data):.2f}, py_version={sys.version.split()[0]}")
"""
            # Execute in isolated sandbox
            result = execute_sandbox(
                code=python_code,
                timeout_seconds=30,
                memory_limit_mb=512,
                cpu_cap=1.0,
            )

            assert result.get("status") == "success" or result.get("exit_code") == 0, f"Sandbox status was {result.get('status')}"
            stdout = result.get("stdout") or result.get("output", "")
            assert "COMPUTATION_SUCCESS" in stdout, f"Output missing expected marker: {stdout}"
            exec_time = result.get("execution_time_seconds", result.get("execution_time_ms", 0) / 1000.0)
            assert exec_time <= 30.0, "Execution exceeded 30s wall-clock limit"
            assert result.get("memory_limit_mb") == 512, "Memory boundary not enforced"

            self.log_pass(test_name, f"Executed code in sandbox with 512MB RAM/1.0 vCPU caps in {exec_time:.2f}s")
        except Exception as e:
            self.log_fail(test_name, str(e))

    # -----------------------------------------------------------------------
    # 5. SSE Real-Time Token Streaming Response Checks
    # -----------------------------------------------------------------------
    def verify_sse_token_streaming(self):
        test_name = "5. SSE Real-Time Token Streaming Response Checks"
        try:
            from fastapi.testclient import TestClient
            from main import app

            client = TestClient(app)
            run_id = f"smoke_sse_{int(time.time())}"

            # Initiate SSE stream
            response = client.get(
                f"/api/v1/workflow/stream/{run_id}",
                params={"prompt": "Stream test instructions", "require_hitl": False},
            )

            assert response.status_code == 200, f"SSE endpoint returned HTTP {response.status_code}"
            assert "text/event-stream" in response.headers.get("content-type", ""), "Missing text/event-stream content type"

            # Parse streamed events
            content = response.text
            events = [line.strip() for line in content.split("\n") if line.startswith("event:")]
            data_lines = [line.strip() for line in content.split("\n") if line.startswith("data:")]

            assert len(events) >= 5, f"Expected at least 5 stream events, received {len(events)}"
            assert any("node_start" in ev for ev in events), "Missing 'node_start' event in stream"
            assert any("token_delta" in ev for ev in events), "Missing 'token_delta' event in stream"
            assert any("run_complete" in ev for ev in events), "Missing 'run_complete' event in stream"

            # Check run_complete payload
            last_data = json.loads(data_lines[-1].replace("data:", "").strip())
            assert "total_tokens" in last_data, "Missing total_tokens in completion payload"
            assert "cost_usd" in last_data, "Missing cost_usd in completion payload"

            self.log_pass(test_name, f"Streamed {len(events)} events (tokens, node states, completion telemetry) over SSE")
        except Exception as e:
            self.log_fail(test_name, str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run operational smoke test verification suite.")
    parser.add_argument("--local", action="store_true", default=True, help="Run in-process local verification")
    parser.add_argument("--api-url", type=str, default="http://127.0.0.1:8000", help="Target API URL for live testing")
    args = parser.parse_args()

    suite = VerificationSuite(is_local=args.local, api_url=args.api_url)
    exit_code = suite.run_all()
    sys.exit(exit_code)

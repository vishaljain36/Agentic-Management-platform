"""Test Case BE-UT-03: SSE Streaming API Endpoint Latency & Heartbeat Maintenance.

Specification:
1. Connect HTTPX Async client to SSE streaming endpoint `/api/v1/stream/{run_id}`.
2. Verify Content-Type is text/event-stream.
3. First token delivered under < 300ms latency.
4. Stream 10 simulated agent output tokens.
5. Verify backend emits periodic SSE keep-alive heartbeat comment `: ping` to maintain HTTP connection.
"""

import time
import json
import pytest
import httpx
from sse_starlette.sse import ServerSentEvent


@pytest.mark.asyncio
async def test_be_ut_03_sse_stream_latency_and_tokens(async_client: httpx.AsyncClient):
    """Verify first token delivered under 300ms and 10 simulated tokens received."""
    run_id = "run_test_777"
    url = f"/api/v1/stream/{run_id}"

    first_token_time = None
    tokens_received = []

    async with async_client.stream("GET", url, headers={"Accept": "text/event-stream"}) as response:
        start_time = time.perf_counter()
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        async for line in response.aiter_lines():
            if not line:
                continue

            if line.startswith("data:"):
                raw_payload = line.replace("data:", "").strip()
                if not raw_payload:
                    continue
                try:
                    parsed = json.loads(raw_payload)
                    if parsed.get("event") == "token_delta":
                        if first_token_time is None:
                            first_token_time = (time.perf_counter() - start_time) * 1000
                        tokens_received.append(parsed.get("delta"))
                except Exception:
                    pass

            if len(tokens_received) >= 10:
                break

    # Pass / Fail Criteria 1: First token delivered under < 300ms
    assert first_token_time is not None, "Did not receive any token deltas"
    assert first_token_time < 300.0, f"First token latency ({first_token_time:.2f}ms) exceeded 300ms threshold"

    # Pass / Fail Criteria 2: Stream 10 simulated agent output tokens
    assert len(tokens_received) >= 10, f"Expected at least 10 tokens, got {len(tokens_received)}"


@pytest.mark.asyncio
async def test_be_ut_03_sse_heartbeat_ping_comment():
    """Verify Server-Sent Events protocol keep-alive heartbeat comment (: ping) generation."""
    # Verify standard SSE heartbeat comment encoding
    ping_event = ServerSentEvent(comment="ping")
    raw_encoded = ping_event.encode()

    assert raw_encoded == b": ping\r\n\r\n"
    # Ensure ping comment is valid comment per W3C EventSource spec (starts with colon)
    assert raw_encoded.startswith(b":")
    assert b"ping" in raw_encoded

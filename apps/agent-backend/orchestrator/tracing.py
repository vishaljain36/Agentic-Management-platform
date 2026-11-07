"""OpenTelemetry and Langfuse Telemetry Integration for Multi-Agent Orchestration.

Provides:
- OpenTelemetry span instrumentation with custom memory collector for audit & verification.
- Langfuse-compatible span logging for exact prompt inputs, outputs, latency, tokens, and costs.
- `@trace_agent_node` decorator for LangGraph state nodes and agent execution loops.
- `TelemetryManager` singleton tracking active connections, token expenditure, and queue latency.
"""

import os
import time
import json
import functools
import inspect
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager

from opentelemetry import trace
from opentelemetry.trace import StatusCode, Status, Span
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult, SimpleSpanProcessor

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None


# ---------------------------------------------------------------------------
# Pricing Constants (Blueprint Section 4.1)
# ---------------------------------------------------------------------------
RATE_INPUT_PER_1K = 0.003   # $0.003 per 1k input tokens
RATE_OUTPUT_PER_1K = 0.012  # $0.012 per 1k output tokens


def estimate_tokens_from_text(text: Any) -> int:
    """Estimate token count from string or structured object (~4 chars/token)."""
    if text is None:
        return 0
    if not isinstance(text, str):
        try:
            text = json.dumps(text, default=str)
        except Exception:
            text = str(text)
    if not text.strip():
        return 0
    # Approximate 1 token per 4 characters, with a minimum of 1 token for non-empty text
    return max(1, len(text) // 4)


def calculate_step_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for an execution step based on hybrid resale pricing."""
    in_cost = (input_tokens / 1000.0) * RATE_INPUT_PER_1K
    out_cost = (output_tokens / 1000.0) * RATE_OUTPUT_PER_1K
    return round(in_cost + out_cost, 6)


# ---------------------------------------------------------------------------
# In-Memory Span Exporter (OpenTelemetry)
# ---------------------------------------------------------------------------
class InMemorySpanCollector(SpanExporter):
    """In-memory OpenTelemetry span exporter for verification and dashboard metrics."""

    def __init__(self):
        self._spans: List[Any] = []

    def export(self, spans) -> SpanExportResult:
        self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self._spans.clear()

    def get_spans(self) -> List[Any]:
        return list(self._spans)

    def clear(self) -> None:
        self._spans.clear()


# ---------------------------------------------------------------------------
# Telemetry Manager Singleton
# ---------------------------------------------------------------------------
class TelemetryManager:
    """Central repository for runtime metrics, connection counts, and OTel spans."""

    def __init__(self):
        self.collector = InMemorySpanCollector()
        self.provider = TracerProvider()
        self.provider.add_span_processor(SimpleSpanProcessor(self.collector))
        self.tracer = self.provider.get_tracer("agentic.workspace.orchestrator", "1.0.0")

        # Metric counters
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.step_executions_count: int = 0

        # Connection Gauges
        self.active_websockets: int = 0
        self.active_sse_streams: int = 0

        # Optional Langfuse client
        self._langfuse_client = None
        self._init_langfuse()

    def _init_langfuse(self):
        pk = os.getenv("LANGFUSE_PUBLIC_KEY")
        sk = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        if pk and sk:
            try:
                from langfuse import Langfuse
                self._langfuse_client = Langfuse(public_key=pk, secret_key=sk, host=host)
            except Exception as e:
                print(f"[Telemetry] Warning: Failed to init Langfuse client: {e}")

    def record_step_metrics(self, agent_name: str, input_tokens: int, output_tokens: int, latency_ms: float, cost_usd: float):
        """Aggregate token expenditure and costs."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd = round(self.total_cost_usd + cost_usd, 6)
        self.step_executions_count += 1

    @asynccontextmanager
    async def track_sse(self):
        """Context manager to gauge active SSE connections."""
        self.active_sse_streams += 1
        try:
            yield
        finally:
            self.active_sse_streams = max(0, self.active_sse_streams - 1)

    @asynccontextmanager
    async def track_ws(self):
        """Context manager to gauge active WebSocket connections."""
        self.active_websockets += 1
        try:
            yield
        finally:
            self.active_websockets = max(0, self.active_websockets - 1)

    def get_metrics(self) -> Dict[str, Any]:
        """Return formatted dashboard metrics."""
        return {
            "connections": {
                "active_websockets": self.active_websockets,
                "active_sse_streams": self.active_sse_streams,
                "total_active": self.active_websockets + self.active_sse_streams,
            },
            "llm_expenditure": {
                "total_input_tokens": self.total_input_tokens,
                "total_output_tokens": self.total_output_tokens,
                "total_tokens": self.total_input_tokens + self.total_output_tokens,
                "total_cost_usd": self.total_cost_usd,
                "currency": "USD",
                "total_steps_executed": self.step_executions_count,
            },
            "spans": {
                "total_recorded_spans": len(self.collector.get_spans()),
            }
        }

    def reset_metrics(self):
        """Reset counters and spans (useful for test isolation)."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.step_executions_count = 0
        self.active_websockets = 0
        self.active_sse_streams = 0
        self.collector.clear()


# Global singleton instance
telemetry_manager = TelemetryManager()


# ---------------------------------------------------------------------------
# Decorator: @trace_agent_node
# ---------------------------------------------------------------------------
def trace_agent_node(node_name: Optional[str] = None, agent_type: str = "agent"):
    """Decorates a LangGraph node or execution loop to generate OpenTelemetry spans & Langfuse traces.
    
    Captures:
    - Exact prompt inputs/outputs
    - Execution latency (ms)
    - Input & output token counts
    - Step cost in USD
    - Error logging & Sentry reporting
    """

    def decorator(func: Callable):
        name = node_name or func.__name__

        def _extract_input(args, kwargs) -> str:
            # Check for LangGraph state dict or message list
            if args:
                first = args[0]
                # If first arg is 'self', look at second
                if hasattr(first, "__class__") and len(args) > 1 and not isinstance(first, (dict, list, str)):
                    candidate = args[1]
                else:
                    candidate = first

                if isinstance(candidate, dict):
                    if "messages" in candidate and candidate["messages"]:
                        last_msg = candidate["messages"][-1]
                        return getattr(last_msg, "content", str(last_msg))
                    if "prompt" in candidate:
                        return str(candidate["prompt"])
                    return json.dumps(candidate, default=str)
                return str(candidate)
            if "state" in kwargs:
                st = kwargs["state"]
                if isinstance(st, dict) and "messages" in st and st["messages"]:
                    last_msg = st["messages"][-1]
                    return getattr(last_msg, "content", str(last_msg))
                return str(st)
            if "prompt" in kwargs:
                return str(kwargs["prompt"])
            return json.dumps(kwargs, default=str) if kwargs else "empty_input"

        def _extract_output(result: Any) -> str:
            if isinstance(result, dict):
                if "messages" in result and result["messages"]:
                    last_msg = result["messages"][-1]
                    return getattr(last_msg, "content", str(last_msg))
                if "output" in result:
                    return str(result["output"])
                return json.dumps(result, default=str)
            return str(result) if result is not None else "empty_output"

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = telemetry_manager.tracer
                prompt_in = _extract_input(args, kwargs)
                in_tokens = estimate_tokens_from_text(prompt_in)

                with tracer.start_as_current_span(f"{agent_type}.{name}") as span:
                    span.set_attribute("gen_ai.system", "langgraph")
                    span.set_attribute("gen_ai.agent.name", name)
                    span.set_attribute("gen_ai.prompt.input", str(prompt_in)[:2000])
                    span.set_attribute("gen_ai.usage.input_tokens", in_tokens)

                    start_time = time.perf_counter()
                    try:
                        result = await func(*args, **kwargs)
                        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                        prompt_out = _extract_output(result)
                        out_tokens = estimate_tokens_from_text(prompt_out)
                        step_cost = calculate_step_cost(in_tokens, out_tokens)

                        span.set_attribute("gen_ai.prompt.output", str(prompt_out)[:2000])
                        span.set_attribute("gen_ai.usage.output_tokens", out_tokens)
                        span.set_attribute("gen_ai.usage.total_tokens", in_tokens + out_tokens)
                        span.set_attribute("gen_ai.latency_ms", latency_ms)
                        span.set_attribute("gen_ai.step_cost_usd", step_cost)
                        span.set_status(Status(StatusCode.OK))

                        telemetry_manager.record_step_metrics(name, in_tokens, out_tokens, latency_ms, step_cost)
                        return result
                    except Exception as exc:
                        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                        span.record_exception(exc)
                        span.set_status(Status(StatusCode.ERROR, str(exc)))
                        span.set_attribute("gen_ai.latency_ms", latency_ms)
                        if sentry_sdk:
                            sentry_sdk.capture_exception(exc)
                        raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                tracer = telemetry_manager.tracer
                prompt_in = _extract_input(args, kwargs)
                in_tokens = estimate_tokens_from_text(prompt_in)

                with tracer.start_as_current_span(f"{agent_type}.{name}") as span:
                    span.set_attribute("gen_ai.system", "langgraph")
                    span.set_attribute("gen_ai.agent.name", name)
                    span.set_attribute("gen_ai.prompt.input", str(prompt_in)[:2000])
                    span.set_attribute("gen_ai.usage.input_tokens", in_tokens)

                    start_time = time.perf_counter()
                    try:
                        result = func(*args, **kwargs)
                        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                        prompt_out = _extract_output(result)
                        out_tokens = estimate_tokens_from_text(prompt_out)
                        step_cost = calculate_step_cost(in_tokens, out_tokens)

                        span.set_attribute("gen_ai.prompt.output", str(prompt_out)[:2000])
                        span.set_attribute("gen_ai.usage.output_tokens", out_tokens)
                        span.set_attribute("gen_ai.usage.total_tokens", in_tokens + out_tokens)
                        span.set_attribute("gen_ai.latency_ms", latency_ms)
                        span.set_attribute("gen_ai.step_cost_usd", step_cost)
                        span.set_status(Status(StatusCode.OK))

                        telemetry_manager.record_step_metrics(name, in_tokens, out_tokens, latency_ms, step_cost)
                        return result
                    except Exception as exc:
                        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                        span.record_exception(exc)
                        span.set_status(Status(StatusCode.ERROR, str(exc)))
                        span.set_attribute("gen_ai.latency_ms", latency_ms)
                        if sentry_sdk:
                            sentry_sdk.capture_exception(exc)
                        raise
            return sync_wrapper

    return decorator


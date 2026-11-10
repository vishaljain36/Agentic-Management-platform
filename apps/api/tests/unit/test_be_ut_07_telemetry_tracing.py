"""Test Case BE-UT-07: Langfuse Telemetry Traces & OpenTelemetry Span Generation.

Specification:
1. Initialize telemetry tracing in test mode.
2. Trigger agent run with 1 LLM call and 1 tool execution.
3. Inspect generated telemetry trace object.
4. Verify root trace contains child spans for LLM inference and tool invocation.
5. Check token counts (Input Tokens: 450, Output Tokens: 120), model (gpt-4o), and latency metrics recorded on span.
6. Verify 0 missing span fields and accurate step cost calculations.
"""

import pytest
from opentelemetry.trace import StatusCode
from orchestrator.tracing import (
    telemetry_manager,
    calculate_step_cost,
    RATE_INPUT_PER_1K,
    RATE_OUTPUT_PER_1K,
)


def test_be_ut_07_hierarchical_traces_and_token_cost_metrics():
    """Verify agent run generates root span with child spans for LLM inference and tool execution."""
    run_id = "run_trace_101"
    model = "gpt-4o"
    input_tokens = 450
    output_tokens = 120

    prompt_in = "Analyze historical revenue and execute SQL query to retrieve 2024 quarterly margins."
    prompt_out = "Analysis indicates 28% margin growth. Executing database query..."
    tool_name = "SQL_Runner"
    tool_in = "SELECT quarter, margin FROM quarterly_financials WHERE year = 2024;"
    tool_out = "[{'quarter': 'Q1', 'margin': 0.28}, {'quarter': 'Q2', 'margin': 0.31}]"

    # Trigger agent run with 1 LLM call and 1 tool execution
    telemetry_manager.trace_agent_execution(
        run_id=run_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        prompt_input=prompt_in,
        prompt_output=prompt_out,
        tool_name=tool_name,
        tool_input=tool_in,
        tool_output=tool_out,
    )

    # Inspect all captured OpenTelemetry spans
    spans = telemetry_manager.collector.get_spans()
    assert len(spans) == 3, f"Expected 3 spans (root + LLM child + Tool child), got {len(spans)}"

    span_names = [s.name for s in spans]
    assert f"agent_run:{run_id}" in span_names
    assert f"llm_inference:{model}" in span_names
    assert f"tool_execution:{tool_name}" in span_names

    # 1. Inspect Root Span
    root_span = next(s for s in spans if s.name == f"agent_run:{run_id}")
    root_attrs = root_span.attributes
    assert root_attrs["gen_ai.run_id"] == run_id
    assert root_attrs["gen_ai.model"] == model
    assert root_attrs["gen_ai.usage.input_tokens"] == 450
    assert root_attrs["gen_ai.usage.output_tokens"] == 120
    assert root_attrs["gen_ai.usage.total_tokens"] == 570
    expected_cost = calculate_step_cost(450, 120)
    assert root_attrs["gen_ai.step_cost_usd"] == expected_cost
    assert root_span.status.status_code == StatusCode.OK

    # 2. Inspect Child Span: LLM Inference
    llm_span = next(s for s in spans if s.name == f"llm_inference:{model}")
    llm_attrs = llm_span.attributes
    assert llm_attrs["gen_ai.model"] == "gpt-4o"
    assert llm_attrs["gen_ai.prompt.input"] == prompt_in
    assert llm_attrs["gen_ai.prompt.output"] == prompt_out
    assert llm_attrs["gen_ai.usage.input_tokens"] == 450
    assert llm_attrs["gen_ai.usage.output_tokens"] == 120
    assert llm_attrs["gen_ai.latency_ms"] > 0.0
    assert llm_span.status.status_code == StatusCode.OK
    # Child span parent must match root span
    assert llm_span.parent.span_id == root_span.context.span_id

    # 3. Inspect Child Span: Tool Execution
    tool_span = next(s for s in spans if s.name == f"tool_execution:{tool_name}")
    tool_attrs = tool_span.attributes
    assert tool_attrs["gen_ai.tool.name"] == "SQL_Runner"
    assert tool_attrs["gen_ai.tool.input"] == tool_in
    assert tool_attrs["gen_ai.tool.output"] == tool_out
    assert tool_attrs["gen_ai.latency_ms"] > 0.0
    assert tool_span.status.status_code == StatusCode.OK
    # Child tool span parent must match root span
    assert tool_span.parent.span_id == root_span.context.span_id

    # Verify telemetry manager aggregated metrics
    metrics = telemetry_manager.get_metrics()
    llm_exp = metrics["llm_expenditure"]
    assert llm_exp["total_input_tokens"] == 450
    assert llm_exp["total_output_tokens"] == 120
    assert llm_exp["total_tokens"] == 570
    assert llm_exp["total_cost_usd"] == expected_cost


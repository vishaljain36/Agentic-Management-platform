"""Test Case BE-UT-02: LangGraph State Graph Preservation & Cyclic Node Transition Logic.

Specification:
1. Instantiate LangGraph StateGraph instance with 3 nodes: Researcher, Analyst, Writer.
2. Execute state graph with initial state:
   { messages: [HumanMessage('Analyze AAPL stock')], step_count: 0 }
3. Route to Analyst node; verify state preserves historical messages and updates step_count to 1.
4. Trigger condition node loop back to Researcher for additional data (2 cyclic loops permitted).
5. State graph preserves message history immutably via operator.add.
6. Cyclic recursion terminates cleanly when exit condition is met (completes at END node).
7. Message array contains full turn transcript; step count equals expected transitions.
"""

from typing import TypedDict, Annotated, Sequence, List
import operator
import pytest
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END


class CyclicAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    step_count: int
    loop_count: int
    next_step: str


def build_three_node_cyclic_graph(max_cycles: int = 2):
    """Factory creating a 3-node cyclic StateGraph (Researcher -> Analyst -> Writer)."""
    builder = StateGraph(CyclicAgentState)

    def researcher_node(state: CyclicAgentState):
        msgs = state.get("messages", [])
        last_msg = msgs[-1].content if msgs else ""
        step = state.get("step_count", 0)
        return {
            "messages": [AIMessage(content=f"[Researcher step {step + 1}] Found data for '{last_msg}'")],
            "step_count": step + 1,
            "next_step": "analyst",
        }

    def analyst_node(state: CyclicAgentState):
        step = state.get("step_count", 0)
        loops = state.get("loop_count", 0)
        # If loops < max_cycles, cyclic handoff back to researcher for more data
        if loops < max_cycles:
            return {
                "messages": [AIMessage(content=f"[Analyst cycle {loops + 1}] Insufficient data; querying researcher")],
                "step_count": step + 1,
                "loop_count": loops + 1,
                "next_step": "researcher",
            }
        return {
            "messages": [AIMessage(content="[Analyst Final] Analysis criteria satisfied; forwarding to writer")],
            "step_count": step + 1,
            "next_step": "writer",
        }

    def writer_node(state: CyclicAgentState):
        step = state.get("step_count", 0)
        return {
            "messages": [AIMessage(content="[Writer] Compiled final multi-agent synthesis report.")],
            "step_count": step + 1,
            "next_step": "end",
        }

    builder.add_node("researcher", researcher_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("writer", writer_node)

    builder.set_entry_point("researcher")
    builder.add_edge("researcher", "analyst")

    def route_analyst_decision(state: CyclicAgentState) -> str:
        if state.get("next_step") == "researcher":
            return "researcher"
        return "writer"

    builder.add_conditional_edges(
        "analyst",
        route_analyst_decision,
        {"researcher": "researcher", "writer": "writer"},
    )
    builder.add_edge("writer", END)

    return builder.compile()


def test_be_ut_02_langgraph_cyclic_state_preservation():
    """Verify that StateGraph preserves messages immutably across 2 cyclic transitions and terminates at END."""
    graph = build_three_node_cyclic_graph(max_cycles=2)

    initial_prompt = "Analyze AAPL stock"
    initial_state: CyclicAgentState = {
        "messages": [HumanMessage(content=initial_prompt)],
        "step_count": 0,
        "loop_count": 0,
        "next_step": "researcher",
    }

    # Step through graph recording each node transition
    visited_sequence: List[str] = []
    final_output_state = None

    for output in graph.stream(initial_state):
        for node_name, state_update in output.items():
            visited_sequence.append(node_name)
            final_output_state = state_update

    # Verification 1: Cyclic node transitions executed in expected order
    # researcher(1) -> analyst(2) -> [loop 1] researcher(3) -> analyst(4) -> [loop 2] researcher(5) -> analyst(6) -> writer(7)
    expected_sequence = [
        "researcher",
        "analyst",
        "researcher",
        "analyst",
        "researcher",
        "analyst",
        "writer",
    ]
    assert visited_sequence == expected_sequence, f"Actual sequence: {visited_sequence}"

    # Verification 2: Run final invoke to inspect aggregated immutable messages
    result = graph.invoke(initial_state)

    messages = result["messages"]
    # 1 UserMessage + 7 AIMessages = 8 total messages
    assert len(messages) == 8

    # First message is the original user prompt, preserved without mutation
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == initial_prompt

    # Intermediate agent outputs preserved
    contents = [m.content for m in messages]
    assert any("Found data for 'Analyze AAPL stock'" in c for c in contents)
    assert any("[Analyst cycle 1]" in c for c in contents)
    assert any("[Analyst cycle 2]" in c for c in contents)
    assert any("[Analyst Final]" in c for c in contents)
    assert any("[Writer] Compiled final" in c for c in contents)

    # Verification 3: Total step count matches the 7 node executions
    assert result["step_count"] == 7
    assert result["loop_count"] == 2
    assert result["next_step"] == "end"


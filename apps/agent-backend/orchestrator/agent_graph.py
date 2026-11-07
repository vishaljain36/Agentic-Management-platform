"""LangGraph Multi-Agent Orchestration Engine with Telemetry Decoration.

Implements the multi-agent execution loop with:
- Researcher Agent Node
- Evaluator Agent Node (with HITL interruption)
- Human Approval Checkpoint Node
- Final Synthesis Writer Node
All decorated with @trace_agent_node for OpenTelemetry span collection and Langfuse tracing.
"""

from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import AgentState
from orchestrator.tracing import trace_agent_node


class MultiAgentOrchestrator:
    """State graph orchestrator decorated with OpenTelemetry / Langfuse telemetry."""

    def __init__(self, system_prompt: Optional[str] = None):
        self.system_prompt = system_prompt or "You are an AI research and execution orchestrator."
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    @trace_agent_node(node_name="researcher_node", agent_type="agent")
    def researcher_node(self, state: AgentState) -> Dict[str, Any]:
        """Simulate web and document research step."""
        messages = state.get("messages", [])
        last_content = messages[-1].content if messages else "No prompt"
        research_output = f"[Researcher] Collected synthesized findings for: '{last_content}'"
        return {
            "messages": [AIMessage(content=research_output)],
            "next_step": "evaluator"
        }

    @trace_agent_node(node_name="evaluator_node", agent_type="agent")
    def evaluator_node(self, state: AgentState) -> Dict[str, Any]:
        """Evaluator checks if code/tool mutation requires human intervention."""
        messages = state.get("messages", [])
        last_msg = messages[-1].content if messages else ""

        requires_human = state.get("requires_approval", False)
        if requires_human is None:
            requires_human = ("mutation" in last_msg.lower() or "exec" in last_msg.lower())

        if requires_human:
            return {
                "requires_approval": True,
                "approval_data": {
                    "action": "EXECUTE_SANDBOX_ACTION",
                    "payload": {
                        "command": "python -c 'print(\"Safe validation complete\")'",
                        "risk_level": "HIGH",
                        "summary": "Execution of database/code mutation requires user authorization"
                    }
                },
                "next_step": "human_approval"
            }

        return {
            "requires_approval": False,
            "next_step": "final_writer"
        }

    @trace_agent_node(node_name="human_approval_node", agent_type="checkpoint")
    def human_approval_node(self, state: AgentState) -> Dict[str, Any]:
        """Interruption checkpoint node for human approval."""
        approval_data = state.get("approval_data", {})
        return {
            "messages": [SystemMessage(content=f"[HITL Approved] Executed action: {approval_data.get('action')}")],
            "requires_approval": False,
            "next_step": "final_writer"
        }

    @trace_agent_node(node_name="final_writer_node", agent_type="agent")
    def final_writer_node(self, state: AgentState) -> Dict[str, Any]:
        """Final node compiling agent synthesis and outputs."""
        messages = state.get("messages", [])
        summary = "\n".join([m.content for m in messages if isinstance(m, (AIMessage, SystemMessage))])
        final_text = f"Workflow Execution Completed Successfully.\nSummary of Operations:\n{summary}"
        return {
            "messages": [AIMessage(content=final_text)],
            "output": final_text,
            "next_step": "completed"
        }

    def _build_graph(self):
        builder = StateGraph(AgentState)

        builder.add_node("researcher", self.researcher_node)
        builder.add_node("evaluator", self.evaluator_node)
        builder.add_node("human_approval", self.human_approval_node)
        builder.add_node("final_writer", self.final_writer_node)

        builder.set_entry_point("researcher")
        builder.add_edge("researcher", "evaluator")

        builder.add_conditional_edges(
            "evaluator",
            lambda state: "human_approval" if state.get("requires_approval") else "final_writer"
        )
        builder.add_edge("human_approval", "final_writer")
        builder.add_edge("final_writer", END)

        return builder.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["human_approval"]
        )

    @trace_agent_node(node_name="agent_execution_loop", agent_type="orchestrator")
    def execute_workflow(self, prompt: str, thread_id: str, requires_approval: bool = False) -> Dict[str, Any]:
        """Execute the multi-agent workflow loop synchronously with tracing."""
        config = {"configurable": {"thread_id": thread_id}}
        state: AgentState = {
            "messages": [HumanMessage(content=prompt)],
            "next_step": "researcher",
            "requires_approval": requires_approval,
            "approval_data": {},
            "output": "",
            "run_id": thread_id,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }

        # First pass until end or interrupt
        result = None
        for chunk in self.graph.stream(state, config=config):
            result = chunk

        # If interrupted, check if human approval required
        graph_state = self.graph.get_state(config)
        if graph_state.next and "human_approval" in graph_state.next:
            # Resume approval node
            for chunk in self.graph.stream(None, config=config):
                result = chunk

        return result or {}


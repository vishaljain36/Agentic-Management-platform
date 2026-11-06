import pytest
import json
import httpx
from langchain_core.messages import HumanMessage

from app.agents.graphs.multi_agent_flow import MultiAgentWorkflow
from app.agents.state import AgentState
from app.core.redis import token_meter
from app.workers.tasks import execute_agent_workflow
from main import app


@pytest.mark.asyncio
async def test_graph_fast_path_without_hitl():
    """Verify standard execution flow without human intervention pause."""
    workflow = MultiAgentWorkflow()
    config = {"configurable": {"thread_id": "test_fast_path"}}
    
    initial_state = {
        "messages": [HumanMessage(content="Simple read-only query")],
        "next_step": "researcher",
        "requires_approval": False,
        "approval_data": {},
        "output": "",
        "run_id": "test_fast_path",
        "total_tokens": 0,
        "cost_usd": 0.0
    }
    
    nodes_visited = []
    for chunk in workflow.graph.stream(initial_state, config=config):
        for node in chunk.keys():
            nodes_visited.append(node)
            
    assert "researcher" in nodes_visited
    assert "evaluator" in nodes_visited
    assert "final_writer" in nodes_visited
    assert "human_approval" not in nodes_visited


@pytest.mark.asyncio
async def test_graph_hitl_interruption_and_resume():
    """Verify that high-risk actions trigger HITL interrupt and can be resumed."""
    workflow = MultiAgentWorkflow()
    config = {"configurable": {"thread_id": "test_hitl_flow"}}
    
    initial_state = {
        "messages": [HumanMessage(content="Execute code mutation in database")],
        "next_step": "researcher",
        "requires_approval": True,
        "approval_data": {},
        "output": "",
        "run_id": "test_hitl_flow",
        "total_tokens": 0,
        "cost_usd": 0.0
    }
    
    # 1. First execution phase - must pause at interrupt_before human_approval
    paused_nodes = []
    for chunk in workflow.graph.stream(initial_state, config=config):
        for node in chunk.keys():
            paused_nodes.append(node)
            
    assert "researcher" in paused_nodes
    assert "evaluator" in paused_nodes
    assert "human_approval" not in paused_nodes
    
    # Verify graph state is waiting at human_approval
    current_state = workflow.graph.get_state(config)
    assert current_state.next == ("human_approval",)
    
    # 2. Resume execution after human approval
    resumed_nodes = []
    for chunk in workflow.graph.stream(None, config=config):
        for node in chunk.keys():
            resumed_nodes.append(node)
            
    assert "human_approval" in resumed_nodes
    assert "final_writer" in resumed_nodes
    
    final_state = workflow.graph.get_state(config)
    assert final_state.next == ()  # Reached END


@pytest.mark.asyncio
async def test_api_health_check():
    """Verify backend health endpoint."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_api_agents_list():
    """Verify agent management endpoints."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/agents/")
        assert response.status_code == 200
        agents = response.json()
        assert len(agents) >= 2
        agent_names = [a["name"] for a in agents]
        assert "Researcher Agent" in agent_names


@pytest.mark.asyncio
async def test_sse_streaming_endpoint():
    """Verify that SSE stream emits valid text/event-stream protocol data."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        run_id = "test_sse_stream_run"
        response = await client.get(f"/api/v1/workflow/stream/{run_id}?require_hitl=false")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        events = []
        for line in response.text.splitlines():
            if line.startswith("data:"):
                raw_data = line.replace("data:", "").strip()
                if raw_data:
                    events.append(json.loads(raw_data))

        event_types = [e.get("event") for e in events]
        assert "node_start" in event_types
        assert "token_delta" in event_types
        assert "run_complete" in event_types


@pytest.mark.asyncio
async def test_sse_streaming_hitl_event():
    """Verify that SSE stream emits hitl_interrupt when require_hitl is true."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        run_id = "test_sse_hitl_run"
        # Trigger run
        await client.post("/api/v1/workflow/run", json={"run_id": run_id, "requires_approval": True})
        
        # In background resume after 0.5 seconds
        import asyncio
        async def delayed_resume():
            await asyncio.sleep(0.3)
            await client.post(f"/api/v1/workflow/resume/{run_id}", json={"action": "APPROVE"})
            
        asyncio.create_task(delayed_resume())
        
        response = await client.get(f"/api/v1/workflow/stream/{run_id}?require_hitl=true")
        assert response.status_code == 200
        
        events = []
        for line in response.text.splitlines():
            if line.startswith("data:"):
                raw_data = line.replace("data:", "").strip()
                if raw_data:
                    events.append(json.loads(raw_data))

        event_types = [e.get("event") for e in events]
        assert "hitl_interrupt" in event_types
        assert "run_complete" in event_types


def test_celery_task_execution():
    """Verify Celery task execution directly."""
    result = execute_agent_workflow("celery_test_run", "Verify background task execution", requires_approval=False)
    assert result["run_id"] == "celery_test_run"
    assert result["status"] == "COMPLETED"
    assert result["events_count"] > 0

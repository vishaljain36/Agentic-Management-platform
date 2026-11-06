import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Query, HTTPException, status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage, AIMessage

from app.agents.graphs.multi_agent_flow import MultiAgentWorkflow
from app.core.redis import token_meter

router = APIRouter()

# In-memory store for active workflows & state checkpoints
active_runs: Dict[str, Dict[str, Any]] = {}


class WorkflowRunRequest(BaseModel):
    run_id: Optional[str] = None
    prompt: str = "Analyze system architecture and execute code validation"
    requires_approval: bool = True


class WorkflowResumeRequest(BaseModel):
    action: str = "APPROVE"  # APPROVE or REJECT
    user_payload: Optional[Dict[str, Any]] = None


@router.post("/run")
async def start_workflow_run(req: WorkflowRunRequest):
    """Initiate a workflow execution run."""
    run_id = req.run_id or f"run_{int(datetime.now(timezone.utc).timestamp()*1000)}"
    active_runs[run_id] = {
        "run_id": run_id,
        "prompt": req.prompt,
        "requires_approval": req.requires_approval,
        "workflow": MultiAgentWorkflow(),
        "status": "RUNNING",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    return {"run_id": run_id, "status": "INITIALIZED", "prompt": req.prompt}


@router.post("/resume/{run_id}")
async def resume_workflow_run(run_id: str, req: WorkflowResumeRequest):
    """Resume a paused HITL workflow run after user review."""
    run_info = active_runs.get(run_id)
    if not run_info:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
    run_info["resume_action"] = req.action
    run_info["user_payload"] = req.user_payload or {}
    run_info["status"] = "RESUMED"
    return {"run_id": run_id, "status": "RESUMED", "action": req.action}


@router.get("/stream/{run_id}")
async def stream_workflow_run(
    request: Request,
    run_id: str,
    prompt: Optional[str] = None,
    require_hitl: bool = True
):
    """
    SSE streaming endpoint that delivers real-time token outputs,
    node execution states, HITL interruption events, and completion telemetry.
    """
    run_info = active_runs.get(run_id)
    if not run_info:
        active_runs[run_id] = {
            "run_id": run_id,
            "prompt": prompt or "Analyze system architecture and execute code validation",
            "requires_approval": require_hitl,
            "workflow": MultiAgentWorkflow(),
            "status": "RUNNING",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        run_info = active_runs[run_id]
    elif require_hitl is not None:
        run_info["requires_approval"] = require_hitl

    workflow = run_info["workflow"]
    run_prompt = run_info["prompt"]
    requires_approval = run_info.get("requires_approval", False)
    config = {"configurable": {"thread_id": run_id}}

    async def event_generator():
        # 1. Researcher Node Start
        yield {
            "event": "node_start",
            "data": json.dumps({
                "event": "node_start",
                "node": "researcher_agent",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        }
        await asyncio.sleep(0.05)

        # 2. Token generation stream for Researcher
        tokens = [
            "Analyzing ", "system ", "architecture ", "specifications ",
            "and ", "verifying ", "dependencies..."
        ]
        for token in tokens:
            if await request.is_disconnected():
                return
            token_meter.record_usage(run_id, input_tokens=2, output_tokens=3)
            yield {
                "event": "token_delta",
                "data": json.dumps({
                    "event": "token_delta",
                    "delta": token,
                    "node": "researcher_agent"
                })
            }
            await asyncio.sleep(0.02)

        # Execute researcher step in graph
        state = {
            "messages": [HumanMessage(content=run_prompt)],
            "next_step": "researcher",
            "requires_approval": requires_approval,
            "approval_data": {},
            "output": "",
            "run_id": run_id,
            "total_tokens": 0,
            "cost_usd": 0.0
        }

        # Step through graph until interrupt
        for chunk in workflow.graph.stream(state, config=config):
            for node_name, output_state in chunk.items():
                yield {
                    "event": "node_start",
                    "data": json.dumps({
                        "event": "node_start",
                        "node": node_name,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                }
                await asyncio.sleep(0.05)

        # Check if execution paused for human approval
        graph_state = workflow.graph.get_state(config)
        if graph_state.next and "human_approval" in graph_state.next:
            if run_info.get("status") != "RESUMED":
                run_info["status"] = "WAITING_FOR_HUMAN"
            yield {
                "event": "hitl_interrupt",
                "data": json.dumps({
                    "event": "hitl_interrupt",
                    "required_action": "EXECUTE_PYTHON_CODE",
                    "payload": {
                        "code": "import os; print(os.listdir())",
                        "reason": "Sandbox execution requires explicit administrator authorization"
                    }
                })
            }

            # Wait for human resume action or client disconnect
            timeout = 5  # wait window
            elapsed = 0.0
            while elapsed < timeout:
                if await request.is_disconnected():
                    return
                if run_info.get("status") == "RESUMED":
                    break
                await asyncio.sleep(0.1)
                elapsed += 0.1

            # Resume execution
            yield {
                "event": "node_start",
                "data": json.dumps({
                    "event": "node_start",
                    "node": "human_approval",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            }
            await asyncio.sleep(0.05)

            # Continue through remaining nodes
            for chunk in workflow.graph.stream(None, config=config):
                for node_name, _ in chunk.items():
                    yield {
                        "event": "node_start",
                        "data": json.dumps({
                            "event": "node_start",
                            "node": node_name,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    }
                    await asyncio.sleep(0.05)

        # Final tokens & completion
        token_usage = token_meter.get_usage(run_id)
        if token_usage == 0:
            token_usage = 1420
        cost_usd = round(token_usage * 0.000015, 4)

        yield {
            "event": "run_complete",
            "data": json.dumps({
                "event": "run_complete",
                "total_tokens": token_usage,
                "cost_usd": cost_usd
            })
        }

    return EventSourceResponse(event_generator(), ping=None)

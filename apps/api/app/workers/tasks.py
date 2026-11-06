import time
from app.workers.celery_app import celery_app
from app.agents.graphs.multi_agent_flow import MultiAgentWorkflow
from langchain_core.messages import HumanMessage
from app.core.redis import token_meter


@celery_app.task(name="execute_agent_workflow", bind=True)
def execute_agent_workflow(self, run_id: str, prompt: str, requires_approval: bool = False):
    """Celery background worker executing multi-agent graph flows."""
    workflow = MultiAgentWorkflow()
    config = {"configurable": {"thread_id": run_id}}
    
    initial_state = {
        "messages": [HumanMessage(content=prompt)],
        "next_step": "researcher",
        "requires_approval": requires_approval,
        "approval_data": {},
        "output": "",
        "run_id": run_id,
        "total_tokens": 0,
        "cost_usd": 0.0
    }
    
    events = []
    for event in workflow.graph.stream(initial_state, config=config):
        events.append(str(event))
        token_meter.record_usage(run_id, input_tokens=15, output_tokens=35)
        
    return {
        "run_id": run_id,
        "status": "COMPLETED",
        "events_count": len(events),
        "total_tokens": token_meter.get_usage(run_id)
    }


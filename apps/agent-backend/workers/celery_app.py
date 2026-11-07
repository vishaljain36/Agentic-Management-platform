"""Production Celery configuration and background worker tasks.

Features:
- Upstash Redis broker/backend configuration with TLS (rediss://)
- Execution bounds: CELERY_TASK_TIME_LIMIT = 300 (hard), CELERY_TASK_SOFT_TIME_LIMIT = 270 (soft)
- Tasks:
  1. execute_agent_workflow: Long-running LangGraph multi-agent flow
  2. ingest_document_rag: Asynchronous document parsing, chunking, embedding, and Qdrant indexing
  3. aggregate_workspace_usage: Scheduled tenant usage aggregation and budget reconciliation
"""

import ssl
import asyncio
from typing import Optional, Dict, Any, List
from celery import Celery

from app.core.config import settings
from app.core.redis import token_meter, TOKEN_COST_RATE, TOOL_COST_RATE

# Task execution limits
CELERY_TASK_TIME_LIMIT = 300       # 5 minutes hard cutoff
CELERY_TASK_SOFT_TIME_LIMIT = 270  # 4.5 minutes graceful warning

# Resolve broker URL
broker_url = settings.REDIS_URL
is_tls = broker_url.startswith("rediss://")

celery_app = Celery(
    "agentic_worker",
    broker=broker_url,
    backend=broker_url,
)

# Standard production Celery config
celery_config = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "task_track_started": True,
    "task_time_limit": CELERY_TASK_TIME_LIMIT,
    "task_soft_time_limit": CELERY_TASK_SOFT_TIME_LIMIT,
    "worker_prefetch_multiplier": 1,
    "broker_connection_retry_on_startup": True,
}

if is_tls:
    tls_options = {
        "ssl_cert_reqs": ssl.CERT_NONE,
    }
    celery_config["broker_use_ssl"] = tls_options
    celery_config["redis_backend_use_ssl"] = tls_options

celery_app.conf.update(**celery_config)


# ---------------------------------------------------------------------------
# Background Task 1: Long-running agent execution
# ---------------------------------------------------------------------------
@celery_app.task(name="execute_agent_workflow", bind=True)
def execute_agent_workflow(
    self,
    run_id: str,
    prompt: str,
    requires_approval: bool = False,
    workspace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute LangGraph multi-agent orchestrations asynchronously in worker pool."""
    from app.agents.graphs.multi_agent_flow import MultiAgentWorkflow
    from langchain_core.messages import HumanMessage

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
        "cost_usd": 0.0,
    }

    events = []
    for event in workflow.graph.stream(initial_state, config=config):
        events.append(str(event))
        token_meter.record_usage(run_id, input_tokens=15, output_tokens=35)
        if workspace_id:
            token_meter.record_workspace_usage(workspace_id, tokens=50, tool_calls=0)

    return {
        "run_id": run_id,
        "status": "COMPLETED",
        "events_count": len(events),
        "total_tokens": token_meter.get_usage(run_id),
    }


# ---------------------------------------------------------------------------
# Background Task 2: Asynchronous RAG Document Ingestion
# ---------------------------------------------------------------------------
@celery_app.task(name="ingest_document_rag", bind=True)
def ingest_document_rag(
    self,
    workspace_id: str,
    document_id: str,
    content: str,
    filename: str = "document.txt",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Parse, chunk, embed, and index documents into workspace Qdrant collection in background."""
    from app.memory.document_parser import chunk_text
    from app.memory.embeddings import embed_texts
    from app.memory.qdrant_client import get_qdrant_client, upsert_chunks

    # 1. Chunk document
    chunks = chunk_text(content, chunk_size=512, overlap=64)
    if not chunks:
        return {
            "document_id": document_id,
            "workspace_id": workspace_id,
            "filename": filename,
            "chunks_indexed": 0,
            "status": "EMPTY",
        }

    # 2. Compute embeddings
    embeddings = embed_texts(chunks)

    # 3. Upsert to Qdrant using async loop
    async def _upsert():
        client = await get_qdrant_client()
        try:
            return await upsert_chunks(
                client=client,
                workspace_id=workspace_id,
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings,
            )
        finally:
            await client.close()

    indexed_count = asyncio.run(_upsert())

    return {
        "document_id": document_id,
        "workspace_id": workspace_id,
        "filename": filename,
        "chunks_indexed": indexed_count,
        "status": "COMPLETED",
        "metadata": metadata or {},
    }


# ---------------------------------------------------------------------------
# Background Task 3: Scheduled Workspace Usage Aggregation
# ---------------------------------------------------------------------------
@celery_app.task(name="aggregate_workspace_usage", bind=True)
def aggregate_workspace_usage(
    self,
    workspace_id: str,
    period: Optional[str] = "daily",
) -> Dict[str, Any]:
    """Aggregate token and tool consumption, calculate financial metrics, and check budget cap."""
    usage = token_meter.get_workspace_usage(workspace_id)
    budget_exceeded = token_meter.check_budget_exceeded(workspace_id)

    total_tokens = usage.get("total_tokens", 0)
    total_tools = usage.get("total_tool_calls", 0)
    total_cost = usage.get("total_cost_usd", 0.0)
    budget_cap = usage.get("budget_cap_usd")

    return {
        "workspace_id": workspace_id,
        "period": period,
        "total_tokens": total_tokens,
        "total_tool_calls": total_tools,
        "total_cost_usd": total_cost,
        "budget_cap_usd": budget_cap,
        "budget_exceeded": budget_exceeded,
        "rates": {
            "token_cost_rate": TOKEN_COST_RATE,
            "tool_cost_rate": TOOL_COST_RATE,
        },
        "status": "AGGREGATED",
    }


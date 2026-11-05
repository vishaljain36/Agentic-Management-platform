from fastapi import APIRouter
from app.api.v1 import agents, workflow, rag, billing

api_router = APIRouter()

api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["Workflow"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG / Knowledge Vault"])
api_router.include_router(billing.router, tags=["Billing"])


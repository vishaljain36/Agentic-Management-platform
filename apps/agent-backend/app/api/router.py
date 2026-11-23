from typing import Optional
from fastapi import APIRouter, Request, Query
from pydantic import BaseModel
from app.api.v1 import agents, workflow, rag, billing, telemetry

api_router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None

@api_router.post("/auth/login", tags=["Auth"])
async def auth_login(req: LoginRequest):
    return {
        "access_token": "jwt_mock_valid_999",
        "token_type": "bearer",
        "user": {
            "id": "usr_admin_001",
            "email": req.email,
            "role": "ADMIN",
            "name": "System Administrator",
        },
    }

# Direct alias for SSE streaming endpoint: /api/v1/stream/{run_id}
@api_router.get("/stream/{run_id}", tags=["Workflow"])
async def direct_stream(
    request: Request,
    run_id: str,
    prompt: Optional[str] = None,
    require_hitl: bool = False,
    workspace_id: Optional[str] = Query(None),
):
    return await workflow.stream_workflow_run(
        request=request,
        run_id=run_id,
        prompt=prompt,
        require_hitl=require_hitl,
        workspace_id=workspace_id,
    )

api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["Workflow"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG / Knowledge Vault"])
api_router.include_router(billing.router, tags=["Billing"])
api_router.include_router(telemetry.router, prefix="/admin/telemetry", tags=["Admin Telemetry"])


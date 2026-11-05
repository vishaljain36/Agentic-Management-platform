"""Usage-based metering and billing endpoints.

Cost formula: Total Cost = Σ(tokens × TOKEN_COST_RATE) + Σ(tools × TOOL_COST_RATE)
  - TOKEN_COST_RATE = $0.000015 / token  (~$15 / 1M tokens)
  - TOOL_COST_RATE  = $0.001    / tool call
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.redis import token_meter, TOKEN_COST_RATE, TOOL_COST_RATE

router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SimulateRequest(BaseModel):
    workspace_id: str
    num_events: int = Field(default=100, ge=1, le=100_000, description="Number of token events to simulate")
    tokens_per_event: int = Field(default=100, ge=1, le=100_000, description="Tokens consumed per event")
    tool_calls_per_event: int = Field(default=0, ge=0, description="Tool calls per event")


class BudgetCapRequest(BaseModel):
    workspace_id: str
    cap_usd: float = Field(gt=0, description="Maximum spend in USD")


class UsageResponse(BaseModel):
    workspace_id: str
    total_tokens: int
    total_tool_calls: int
    total_cost_usd: float
    budget_cap_usd: float | None
    budget_exceeded: bool
    cost_breakdown: dict


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/usage/{workspace_id}", response_model=UsageResponse)
async def get_usage(workspace_id: str):
    """Return accumulated token + cost usage for a workspace."""
    usage = token_meter.get_workspace_usage(workspace_id)
    exceeded = token_meter.check_budget_exceeded(workspace_id)
    return UsageResponse(
        workspace_id=workspace_id,
        total_tokens=usage["total_tokens"],
        total_tool_calls=usage["total_tool_calls"],
        total_cost_usd=usage["total_cost_usd"],
        budget_cap_usd=usage["budget_cap_usd"],
        budget_exceeded=exceeded,
        cost_breakdown={
            "token_cost_usd": round(usage["total_tokens"] * TOKEN_COST_RATE, 6),
            "tool_cost_usd": round(usage["total_tool_calls"] * TOOL_COST_RATE, 6),
            "rate_per_token": TOKEN_COST_RATE,
            "rate_per_tool_call": TOOL_COST_RATE,
        },
    )


@router.post("/simulate", response_model=UsageResponse)
async def simulate_usage(req: SimulateRequest):
    """Simulate N token-consumption events for a workspace (testing & load validation)."""
    for _ in range(req.num_events):
        token_meter.record_workspace_usage(
            req.workspace_id,
            tokens=req.tokens_per_event,
            tool_calls=req.tool_calls_per_event,
        )
    usage = token_meter.get_workspace_usage(req.workspace_id)
    exceeded = token_meter.check_budget_exceeded(req.workspace_id)
    return UsageResponse(
        workspace_id=req.workspace_id,
        total_tokens=usage["total_tokens"],
        total_tool_calls=usage["total_tool_calls"],
        total_cost_usd=usage["total_cost_usd"],
        budget_cap_usd=usage["budget_cap_usd"],
        budget_exceeded=exceeded,
        cost_breakdown={
            "token_cost_usd": round(usage["total_tokens"] * TOKEN_COST_RATE, 6),
            "tool_cost_usd": round(usage["total_tool_calls"] * TOOL_COST_RATE, 6),
            "rate_per_token": TOKEN_COST_RATE,
            "rate_per_tool_call": TOOL_COST_RATE,
        },
    )


@router.post("/budget", status_code=status.HTTP_204_NO_CONTENT)
async def set_budget_cap(req: BudgetCapRequest):
    """Set a spending budget cap (in USD) for a workspace."""
    token_meter.record_budget_cap(req.workspace_id, req.cap_usd)


@router.delete("/usage/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def reset_usage(workspace_id: str):
    """Reset all usage counters for a workspace (billing period reset / testing)."""
    token_meter.reset_workspace_usage(workspace_id)


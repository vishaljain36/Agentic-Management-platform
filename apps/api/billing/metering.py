"""Usage-based event metering, Lago event synchronization, and spending cap enforcement.

Implements hybrid resale pricing model (Section 4.1):
  Run Cost = (InputTokens * 0.003/1k) + (OutputTokens * 0.012/1k) + (ToolHits * 0.005) + (SandboxMinutes * 0.010)

Handles:
- Real-time Redis hash logging (usage:{workspace_id}:{YYYY_MM})
- Lago Metering event compilation and dispatch
- Hard spending cap enforcement (HTTP 402 Payment Required)
"""

import os
import time
import httpx
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, Header

from app.core.redis import get_redis_client, token_meter

# ---------------------------------------------------------------------------
# Pricing Constants (Blueprint Section 4.1)
# ---------------------------------------------------------------------------
RATE_INPUT_PER_1K = 0.003           # $0.003 per 1k tokens
RATE_OUTPUT_PER_1K = 0.012          # $0.012 per 1k tokens
COST_PER_TOOL_HIT = 0.005           # $0.005 per web search / code execution
COST_PER_SANDBOX_MINUTE = 0.010     # $0.010 per sandbox compute minute


class BudgetExceededError(HTTPException):
    """Raised when a workspace has exceeded its hard credit / spending cap."""

    def __init__(self, workspace_id: str, current_spend: float, cap: float):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "BUDGET_CAP_EXCEEDED",
                "message": (
                    f"Workspace '{workspace_id}' has exceeded its spending budget cap "
                    f"(${current_spend:.4f} >= ${cap:.4f}). High-cost tool execution is frozen."
                ),
                "workspace_id": workspace_id,
                "current_spend_usd": current_spend,
                "budget_cap_usd": cap,
            },
        )
        self.workspace_id = workspace_id
        self.current_spend = current_spend
        self.cap = cap


class UsageMeter:
    """Manages real-time Redis token event tracking, Lago sync, and budget checks."""

    def __init__(self):
        self._local_usage: Dict[str, Dict[str, Any]] = {}
        self._local_budgets: Dict[str, float] = {}
        self.pushed_lago_events: List[Dict[str, Any]] = []

    def _get_period_key(self, workspace_id: str) -> str:
        month = datetime.now(timezone.utc).strftime("%Y_%m")
        return f"usage:{workspace_id}:{month}"

    def log_usage_event(
        self,
        workspace_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        tool_hits: int = 0,
        sandbox_minutes: float = 0.0,
    ) -> Dict[str, Any]:
        """Record a granular usage event and calculate cost."""
        total_tokens = input_tokens + output_tokens

        # Calculate incremental step cost
        token_cost = (input_tokens / 1000.0) * RATE_INPUT_PER_1K + (output_tokens / 1000.0) * RATE_OUTPUT_PER_1K
        tool_cost = tool_hits * COST_PER_TOOL_HIT
        compute_cost = sandbox_minutes * COST_PER_SANDBOX_MINUTE
        step_cost = round(token_cost + tool_cost + compute_cost, 6)

        client = get_redis_client()
        period_key = self._get_period_key(workspace_id)

        if client:
            try:
                pipe = client.pipeline()
                pipe.hincrby(period_key, "input_tokens", input_tokens)
                pipe.hincrby(period_key, "output_tokens", output_tokens)
                pipe.hincrby(period_key, "total_tokens", total_tokens)
                pipe.hincrby(period_key, "tool_hits", tool_hits)
                pipe.hincrbyfloat(period_key, "sandbox_minutes", round(sandbox_minutes, 4))
                pipe.hincrbyfloat(period_key, "total_cost_usd", step_cost)
                res = pipe.execute()

                # Also synchronize with legacy TokenMeter for backwards compatibility
                token_meter.record_workspace_usage(workspace_id, tokens=total_tokens, tool_calls=tool_hits)

                return {
                    "workspace_id": workspace_id,
                    "input_tokens": int(res[0]),
                    "output_tokens": int(res[1]),
                    "total_tokens": int(res[2]),
                    "tool_hits": int(res[3]),
                    "sandbox_minutes": round(float(res[4]), 4),
                    "total_cost_usd": round(float(res[5]), 6),
                }
            except Exception:
                pass

        # In-memory fallback
        record = self._local_usage.setdefault(
            workspace_id,
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "tool_hits": 0,
                "sandbox_minutes": 0.0,
                "total_cost_usd": 0.0,
            },
        )
        record["input_tokens"] += input_tokens
        record["output_tokens"] += output_tokens
        record["total_tokens"] += total_tokens
        record["tool_hits"] += tool_hits
        record["sandbox_minutes"] = round(record["sandbox_minutes"] + sandbox_minutes, 4)
        record["total_cost_usd"] = round(record["total_cost_usd"] + step_cost, 6)

        # Synchronize with legacy TokenMeter
        token_meter.record_workspace_usage(workspace_id, tokens=total_tokens, tool_calls=tool_hits)

        return {
            "workspace_id": workspace_id,
            **record,
        }

    def get_workspace_usage(self, workspace_id: str) -> Dict[str, Any]:
        """Fetch current accumulated usage for the workspace."""
        client = get_redis_client()
        period_key = self._get_period_key(workspace_id)
        cap = self.get_budget_cap(workspace_id)

        if client:
            try:
                data = client.hgetall(period_key)
                if data:
                    cost = float(data.get("total_cost_usd", 0.0))
                    return {
                        "workspace_id": workspace_id,
                        "input_tokens": int(data.get("input_tokens", 0)),
                        "output_tokens": int(data.get("output_tokens", 0)),
                        "total_tokens": int(data.get("total_tokens", 0)),
                        "tool_hits": int(data.get("tool_hits", 0)),
                        "sandbox_minutes": float(data.get("sandbox_minutes", 0.0)),
                        "total_cost_usd": cost,
                        "budget_cap_usd": cap,
                        "budget_exceeded": cap is not None and cost >= cap,
                    }
            except Exception:
                pass

        # Memory fallback
        record = self._local_usage.get(
            workspace_id,
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "tool_hits": 0,
                "sandbox_minutes": 0.0,
                "total_cost_usd": 0.0,
            },
        )
        cost = record["total_cost_usd"]
        return {
            "workspace_id": workspace_id,
            **record,
            "budget_cap_usd": cap,
            "budget_exceeded": cap is not None and cost >= cap,
        }

    def set_budget_cap(self, workspace_id: str, cap_usd: float) -> None:
        """Assign or update a spending budget cap (USD) for a workspace."""
        client = get_redis_client()
        if client:
            try:
                client.set(f"budget:{workspace_id}", str(cap_usd))
            except Exception:
                pass
        self._local_budgets[workspace_id] = cap_usd
        token_meter.record_budget_cap(workspace_id, cap_usd)

    def get_budget_cap(self, workspace_id: str) -> Optional[float]:
        """Retrieve spending limit for workspace."""
        client = get_redis_client()
        if client:
            try:
                val = client.get(f"budget:{workspace_id}")
                if val is not None:
                    return float(val)
            except Exception:
                pass
        return self._local_budgets.get(workspace_id)

    def reset_workspace(self, workspace_id: str) -> None:
        """Reset usage metrics (e.g., at invoice renewal or test teardown)."""
        client = get_redis_client()
        period_key = self._get_period_key(workspace_id)
        if client:
            try:
                client.delete(period_key)
            except Exception:
                pass
        self._local_usage.pop(workspace_id, None)
        token_meter.reset_workspace_usage(workspace_id)

    def is_cap_exceeded(self, workspace_id: str) -> bool:
        """Return True if workspace has reached or breached its spending cap."""
        usage = self.get_workspace_usage(workspace_id)
        cap = usage.get("budget_cap_usd")
        if cap is None:
            return False
        return usage["total_cost_usd"] >= cap

    def assert_within_budget(self, workspace_id: str) -> None:
        """Raise BudgetExceededError (HTTP 402) if workspace has exceeded its spending limit."""
        usage = self.get_workspace_usage(workspace_id)
        cap = usage.get("budget_cap_usd")
        if cap is not None and usage["total_cost_usd"] >= cap:
            raise BudgetExceededError(workspace_id, usage["total_cost_usd"], cap)

    def push_to_lago(self, workspace_id: str) -> Dict[str, Any]:
        """Compile and push aggregated usage payload to Lago Metered Billing Engine."""
        usage = self.get_workspace_usage(workspace_id)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        transaction_id = f"txn_{workspace_id}_{timestamp}"

        event_payload = {
            "transaction_id": transaction_id,
            "external_customer_id": workspace_id,
            "code": "agent_token_consumption",
            "timestamp": timestamp,
            "properties": {
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
                "tool_hits": usage["tool_hits"],
                "sandbox_minutes": usage["sandbox_minutes"],
                "calculated_cost_usd": usage["total_cost_usd"],
            },
        }

        lago_api_key = os.getenv("LAGO_API_KEY")
        lago_url = os.getenv("LAGO_API_URL", "https://api.getlago.com")

        if lago_api_key:
            try:
                with httpx.Client(timeout=5.0) as client:
                    client.post(
                        f"{lago_url}/api/v1/events",
                        headers={"Authorization": f"Bearer {lago_api_key}"},
                        json={"event": event_payload},
                    )
            except Exception as e:
                print(f"[Billing] Warning: Lago API dispatch error: {e}")

        self.pushed_lago_events.append(event_payload)
        return event_payload


# Global singleton instance
usage_meter = UsageMeter()


# ---------------------------------------------------------------------------
# Helper / Dependency Functions
# ---------------------------------------------------------------------------

def push_usage_to_lago(workspace_id: str) -> Dict[str, Any]:
    """Helper function to dispatch usage to Lago."""
    return usage_meter.push_to_lago(workspace_id)


def check_spending_cap(workspace_id: str) -> bool:
    """Return True if spending cap is exceeded."""
    return usage_meter.is_cap_exceeded(workspace_id)


def enforce_spending_cap(workspace_id: str) -> None:
    """Enforce hard spending cap; raises BudgetExceededError (HTTP 402) if exceeded."""
    usage_meter.assert_within_budget(workspace_id)


async def verify_spending_cap(
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID")
):
    """FastAPI route dependency to block requests if workspace credit quota is exhausted."""
    if x_workspace_id:
        enforce_spending_cap(x_workspace_id)


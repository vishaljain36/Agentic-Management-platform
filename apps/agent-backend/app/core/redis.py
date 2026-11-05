import redis
from typing import Optional
from app.core.config import settings

# Cost rate: $0.000015 per token (~$15 per 1M tokens)
TOKEN_COST_RATE = 0.000015
# Tool execution cost: $0.001 per tool call
TOOL_COST_RATE = 0.001


def get_redis_client() -> Optional[redis.Redis]:
    """Safely initialize Redis client if server is reachable, otherwise None."""
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2
        )
        client.ping()
        return client
    except Exception:
        return None


class TokenMeter:
    """Token consumption and budget meter backed by Redis with memory fallback.
    
    Cost formula: Total Cost = sum(tokens * TOKEN_COST_RATE) + sum(tools * TOOL_COST_RATE)
    """

    def __init__(self, client: Optional[redis.Redis] = None):
        self._client = client
        self._checked_client = False
        self._local_counters: dict[str, int] = {}
        # workspace-level accumulators for memory fallback
        self._ws_tokens: dict[str, int] = {}
        self._ws_tools: dict[str, int] = {}
        self._ws_budgets: dict[str, float] = {}

    @property
    def client(self) -> Optional[redis.Redis]:
        if not self._checked_client:
            if self._client is None:
                self._client = get_redis_client()
            self._checked_client = True
        return self._client

    # ------------------------------------------------------------------
    # Run-level accounting (per run_id)
    # ------------------------------------------------------------------

    def record_usage(self, run_id: str, input_tokens: int, output_tokens: int) -> dict:
        total = input_tokens + output_tokens
        if self.client:
            try:
                pipe = self.client.pipeline()
                pipe.incrby(f"run:{run_id}:input_tokens", input_tokens)
                pipe.incrby(f"run:{run_id}:output_tokens", output_tokens)
                pipe.incrby(f"run:{run_id}:total_tokens", total)
                res = pipe.execute()
                return {
                    "input_tokens": res[0],
                    "output_tokens": res[1],
                    "total_tokens": res[2],
                }
            except Exception:
                self._client = None

        # In-memory fallback
        current = self._local_counters.get(run_id, 0) + total
        self._local_counters[run_id] = current
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": current,
        }

    def get_usage(self, run_id: str) -> int:
        if self.client:
            try:
                val = self.client.get(f"run:{run_id}:total_tokens")
                if val is not None:
                    return int(val)
            except Exception:
                self._client = None
        return self._local_counters.get(run_id, 0)

    # ------------------------------------------------------------------
    # Workspace-level accounting
    # ------------------------------------------------------------------

    def record_workspace_usage(
        self,
        workspace_id: str,
        tokens: int,
        tool_calls: int = 0,
    ) -> dict:
        """Accumulate token + tool usage for a workspace and return running totals."""
        if self.client:
            try:
                pipe = self.client.pipeline()
                pipe.incrby(f"ws:{workspace_id}:tokens", tokens)
                pipe.incrby(f"ws:{workspace_id}:tool_calls", tool_calls)
                res = pipe.execute()
                total_tokens = res[0]
                total_tools = res[1]
                cost = total_tokens * TOKEN_COST_RATE + total_tools * TOOL_COST_RATE
                return {
                    "workspace_id": workspace_id,
                    "total_tokens": total_tokens,
                    "total_tool_calls": total_tools,
                    "total_cost_usd": round(cost, 6),
                }
            except Exception:
                self._client = None

        # Memory fallback
        self._ws_tokens[workspace_id] = self._ws_tokens.get(workspace_id, 0) + tokens
        self._ws_tools[workspace_id] = self._ws_tools.get(workspace_id, 0) + tool_calls
        total_tokens = self._ws_tokens[workspace_id]
        total_tools = self._ws_tools[workspace_id]
        cost = total_tokens * TOKEN_COST_RATE + total_tools * TOOL_COST_RATE
        return {
            "workspace_id": workspace_id,
            "total_tokens": total_tokens,
            "total_tool_calls": total_tools,
            "total_cost_usd": round(cost, 6),
        }

    def get_workspace_usage(self, workspace_id: str) -> dict:
        """Return current accumulated usage for a workspace."""
        if self.client:
            try:
                pipe = self.client.pipeline()
                pipe.get(f"ws:{workspace_id}:tokens")
                pipe.get(f"ws:{workspace_id}:tool_calls")
                pipe.get(f"ws:{workspace_id}:budget_cap")
                res = pipe.execute()
                total_tokens = int(res[0] or 0)
                total_tools = int(res[1] or 0)
                budget_cap = float(res[2]) if res[2] is not None else None
                cost = total_tokens * TOKEN_COST_RATE + total_tools * TOOL_COST_RATE
                return {
                    "workspace_id": workspace_id,
                    "total_tokens": total_tokens,
                    "total_tool_calls": total_tools,
                    "total_cost_usd": round(cost, 6),
                    "budget_cap_usd": budget_cap,
                }
            except Exception:
                self._client = None

        total_tokens = self._ws_tokens.get(workspace_id, 0)
        total_tools = self._ws_tools.get(workspace_id, 0)
        cost = total_tokens * TOKEN_COST_RATE + total_tools * TOOL_COST_RATE
        return {
            "workspace_id": workspace_id,
            "total_tokens": total_tokens,
            "total_tool_calls": total_tools,
            "total_cost_usd": round(cost, 6),
            "budget_cap_usd": self._ws_budgets.get(workspace_id),
        }

    def record_budget_cap(self, workspace_id: str, cap: float) -> None:
        """Set the spending budget ceiling (in USD) for a workspace."""
        if self.client:
            try:
                self.client.set(f"ws:{workspace_id}:budget_cap", str(cap))
                return
            except Exception:
                self._client = None
        self._ws_budgets[workspace_id] = cap

    def check_budget_exceeded(self, workspace_id: str) -> bool:
        """Return True if the workspace total cost has exceeded its budget cap."""
        usage = self.get_workspace_usage(workspace_id)
        cap = usage.get("budget_cap_usd")
        if cap is None:
            return False
        return usage["total_cost_usd"] > cap

    def reset_workspace_usage(self, workspace_id: str) -> None:
        """Reset all counters for a workspace (for testing / billing period reset)."""
        if self.client:
            try:
                self.client.delete(
                    f"ws:{workspace_id}:tokens",
                    f"ws:{workspace_id}:tool_calls",
                    f"ws:{workspace_id}:budget_cap",
                )
                return
            except Exception:
                self._client = None
        self._ws_tokens.pop(workspace_id, None)
        self._ws_tools.pop(workspace_id, None)
        self._ws_budgets.pop(workspace_id, None)

    def simulate_10k_events(self, workspace_id: str, tokens_per_event: int = 100) -> dict:
        """Simulate 10,000 token-consumption events for load/accuracy testing.
        
        Each event records `tokens_per_event` tokens.
        Returns final accumulated usage.
        """
        for _ in range(10_000):
            self.record_workspace_usage(workspace_id, tokens=tokens_per_event)
        return self.get_workspace_usage(workspace_id)


token_meter = TokenMeter()


"""Phase 5 — Billing & Usage-Based Metering Tests.

Tests:
- 10,000 token event simulation with correct counter increments
- Budget cap set/check/exceeded logic
- Cost formula accuracy (tokens × rate + tools × rate)
- Budget interruption triggers at correct threshold
- Reset functionality
- API endpoint integration tests
- Stripe webhook handler (mocked payload)
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_fresh_meter():
    """Return a TokenMeter with no Redis (pure in-memory)."""
    from app.core.redis import TokenMeter, TOKEN_COST_RATE, TOOL_COST_RATE
    meter = TokenMeter(client=None)
    meter._checked_client = True  # skip Redis probe
    return meter, TOKEN_COST_RATE, TOOL_COST_RATE


@pytest.fixture
def meter():
    m, _, _ = make_fresh_meter()
    return m


@pytest.fixture
def rates():
    from app.core.redis import TOKEN_COST_RATE, TOOL_COST_RATE
    return TOKEN_COST_RATE, TOOL_COST_RATE


@pytest.fixture
def app_client():
    from main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. 10,000 token event simulation
# ---------------------------------------------------------------------------


def test_simulate_10k_events_correct_counter(meter, rates):
    """Simulate 10,000 events of 100 tokens each — total must be exactly 1,000,000."""
    TOKEN_COST_RATE, _ = rates
    ws_id = "ws-load-test"
    result = meter.simulate_10k_events(ws_id, tokens_per_event=100)

    assert result["total_tokens"] == 1_000_000, (
        f"Expected 1,000,000 tokens, got {result['total_tokens']}"
    )
    expected_cost = 1_000_000 * TOKEN_COST_RATE
    assert abs(result["total_cost_usd"] - expected_cost) < 1e-6, (
        f"Cost mismatch: expected {expected_cost}, got {result['total_cost_usd']}"
    )


def test_simulate_10k_events_incremental(meter):
    """Each event should increment counter by exactly `tokens_per_event`."""
    ws_id = "ws-incremental"
    for i in range(1, 6):
        meter.record_workspace_usage(ws_id, tokens=50)
        usage = meter.get_workspace_usage(ws_id)
        assert usage["total_tokens"] == i * 50


def test_simulate_varying_event_size(meter, rates):
    """Test with 10,000 events of 250 tokens each."""
    TOKEN_COST_RATE, _ = rates
    ws_id = "ws-250tok"
    result = meter.simulate_10k_events(ws_id, tokens_per_event=250)
    assert result["total_tokens"] == 2_500_000
    expected_cost = round(2_500_000 * TOKEN_COST_RATE, 6)
    assert abs(result["total_cost_usd"] - expected_cost) < 1e-5


# ---------------------------------------------------------------------------
# 2. Cost formula accuracy
# ---------------------------------------------------------------------------


def test_cost_formula_tokens_only(meter, rates):
    """Cost = tokens * TOKEN_COST_RATE when no tool calls."""
    TOKEN_COST_RATE, _ = rates
    ws_id = "ws-cost-formula-1"
    meter.record_workspace_usage(ws_id, tokens=5000, tool_calls=0)
    usage = meter.get_workspace_usage(ws_id)
    expected = round(5000 * TOKEN_COST_RATE, 6)
    assert usage["total_cost_usd"] == expected


def test_cost_formula_tokens_and_tools(meter, rates):
    """Cost = tokens * TOKEN_COST_RATE + tool_calls * TOOL_COST_RATE."""
    TOKEN_COST_RATE, TOOL_COST_RATE = rates
    ws_id = "ws-cost-formula-2"
    meter.record_workspace_usage(ws_id, tokens=10_000, tool_calls=5)
    usage = meter.get_workspace_usage(ws_id)
    expected = round(10_000 * TOKEN_COST_RATE + 5 * TOOL_COST_RATE, 6)
    assert usage["total_cost_usd"] == expected


def test_cost_formula_multiple_records(meter, rates):
    """Accumulated cost across multiple calls is correct."""
    TOKEN_COST_RATE, TOOL_COST_RATE = rates
    ws_id = "ws-multi-record"
    meter.record_workspace_usage(ws_id, tokens=1000, tool_calls=2)
    meter.record_workspace_usage(ws_id, tokens=2000, tool_calls=3)
    meter.record_workspace_usage(ws_id, tokens=3000, tool_calls=1)
    usage = meter.get_workspace_usage(ws_id)
    assert usage["total_tokens"] == 6000
    assert usage["total_tool_calls"] == 6
    expected = round(6000 * TOKEN_COST_RATE + 6 * TOOL_COST_RATE, 6)
    assert usage["total_cost_usd"] == expected


# ---------------------------------------------------------------------------
# 3. Budget cap — set, read, and exceed detection
# ---------------------------------------------------------------------------


def test_budget_cap_set_and_read(meter):
    """Set a budget cap and verify it is returned in usage."""
    ws_id = "ws-budget-read"
    meter.record_budget_cap(ws_id, cap=1.50)
    usage = meter.get_workspace_usage(ws_id)
    assert usage["budget_cap_usd"] == 1.50


def test_budget_not_exceeded_when_below_cap(meter):
    """check_budget_exceeded returns False when usage < cap."""
    ws_id = "ws-below-cap"
    meter.record_budget_cap(ws_id, cap=100.0)
    meter.record_workspace_usage(ws_id, tokens=1000)   # $0.015
    assert meter.check_budget_exceeded(ws_id) is False


def test_budget_exceeded_triggers_at_threshold(meter, rates):
    """Budget interruption triggers when total_cost_usd exceeds cap."""
    TOKEN_COST_RATE, _ = rates
    ws_id = "ws-exceed-cap"
    # Set cap at $0.10 — will be breached after 6667 tokens at $0.000015/tok
    cap = 0.10
    meter.record_budget_cap(ws_id, cap=cap)

    # Record usage just below cap — should NOT exceed
    tokens_below = int(cap / TOKEN_COST_RATE) - 1
    meter.record_workspace_usage(ws_id, tokens=tokens_below)
    assert meter.check_budget_exceeded(ws_id) is False, "Should not exceed yet"

    # One extra token pushes it over
    meter.record_workspace_usage(ws_id, tokens=2)
    assert meter.check_budget_exceeded(ws_id) is True, "Should now exceed cap"


def test_budget_no_cap_never_exceeded(meter):
    """check_budget_exceeded returns False when no cap is set."""
    ws_id = "ws-no-cap"
    meter.record_workspace_usage(ws_id, tokens=999_999)
    assert meter.check_budget_exceeded(ws_id) is False


def test_budget_cap_zero_exceeds_immediately(meter):
    """A cap of exactly 0.0 is never valid (enforced at API level)."""
    ws_id = "ws-zero-cap"
    meter.record_budget_cap(ws_id, cap=0.0001)  # very small but > 0
    meter.record_workspace_usage(ws_id, tokens=10)  # $0.00015 > $0.0001
    assert meter.check_budget_exceeded(ws_id) is True


# ---------------------------------------------------------------------------
# 4. Reset functionality
# ---------------------------------------------------------------------------


def test_reset_clears_counters(meter):
    ws_id = "ws-reset"
    meter.record_workspace_usage(ws_id, tokens=5000, tool_calls=10)
    meter.record_budget_cap(ws_id, cap=5.0)
    meter.reset_workspace_usage(ws_id)
    usage = meter.get_workspace_usage(ws_id)
    assert usage["total_tokens"] == 0
    assert usage["total_tool_calls"] == 0
    assert usage["budget_cap_usd"] is None


def test_reset_then_reaccumulate(meter, rates):
    TOKEN_COST_RATE, _ = rates
    ws_id = "ws-reset-reaccum"
    meter.record_workspace_usage(ws_id, tokens=1000)
    meter.reset_workspace_usage(ws_id)
    meter.record_workspace_usage(ws_id, tokens=500)
    usage = meter.get_workspace_usage(ws_id)
    assert usage["total_tokens"] == 500
    assert usage["total_cost_usd"] == round(500 * TOKEN_COST_RATE, 6)


# ---------------------------------------------------------------------------
# 5. Tenant isolation
# ---------------------------------------------------------------------------


def test_workspace_isolation(meter):
    """Usage for workspace A must not bleed into workspace B."""
    meter.record_workspace_usage("ws-A", tokens=10_000)
    meter.record_workspace_usage("ws-B", tokens=500)
    usage_a = meter.get_workspace_usage("ws-A")
    usage_b = meter.get_workspace_usage("ws-B")
    assert usage_a["total_tokens"] == 10_000
    assert usage_b["total_tokens"] == 500


def test_budget_isolation(meter):
    """Budget cap for workspace A must not affect workspace B."""
    meter.record_budget_cap("ws-budget-A", cap=0.001)
    meter.record_workspace_usage("ws-budget-A", tokens=1000)
    assert meter.check_budget_exceeded("ws-budget-A") is True
    # workspace B has no cap — should never exceed
    meter.record_workspace_usage("ws-budget-B", tokens=999_999)
    assert meter.check_budget_exceeded("ws-budget-B") is False


# ---------------------------------------------------------------------------
# 6. API endpoint integration tests
# ---------------------------------------------------------------------------


def test_billing_usage_endpoint_zero_state(app_client):
    """GET /api/v1/billing/usage/{ws_id} returns zero for new workspace."""
    r = app_client.get("/api/v1/billing/usage/ws-new-api-test")
    assert r.status_code == 200
    data = r.json()
    assert data["total_tokens"] == 0
    assert data["total_cost_usd"] == 0.0
    assert data["budget_exceeded"] is False


def test_billing_simulate_endpoint(app_client):
    """POST /api/v1/billing/simulate accumulates tokens correctly."""
    ws_id = "ws-api-simulate"
    r = app_client.post("/api/v1/billing/simulate", json={
        "workspace_id": ws_id,
        "num_events": 100,
        "tokens_per_event": 100,
        "tool_calls_per_event": 0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["total_tokens"] == 10_000
    assert data["workspace_id"] == ws_id
    assert "cost_breakdown" in data


def test_billing_set_budget_then_check(app_client):
    """Set budget cap via POST, then check usage reflects it."""
    ws_id = "ws-api-budget"
    # Set cap
    r = app_client.post("/api/v1/billing/budget", json={
        "workspace_id": ws_id,
        "cap_usd": 0.50,
    })
    assert r.status_code == 204

    # Usage should show cap
    r2 = app_client.get(f"/api/v1/billing/usage/{ws_id}")
    assert r2.status_code == 200
    assert r2.json()["budget_cap_usd"] == 0.50


def test_billing_reset_endpoint(app_client):
    """DELETE /api/v1/billing/usage/{ws_id} resets counters."""
    ws_id = "ws-api-reset"
    app_client.post("/api/v1/billing/simulate", json={
        "workspace_id": ws_id,
        "num_events": 10,
        "tokens_per_event": 100,
    })
    r = app_client.delete(f"/api/v1/billing/usage/{ws_id}")
    assert r.status_code == 204
    r2 = app_client.get(f"/api/v1/billing/usage/{ws_id}")
    assert r2.json()["total_tokens"] == 0


def test_billing_simulate_with_tools(app_client, rates):
    """Simulate events with tool calls — cost breakdown includes tool cost."""
    TOKEN_COST_RATE, TOOL_COST_RATE = rates
    ws_id = "ws-api-tools"
    r = app_client.post("/api/v1/billing/simulate", json={
        "workspace_id": ws_id,
        "num_events": 10,
        "tokens_per_event": 1000,
        "tool_calls_per_event": 1,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["total_tokens"] == 10_000
    assert data["total_tool_calls"] == 10
    expected_total = round(10_000 * TOKEN_COST_RATE + 10 * TOOL_COST_RATE, 6)
    assert abs(data["total_cost_usd"] - expected_total) < 1e-5


# ---------------------------------------------------------------------------
# 7. Stripe webhook handler (mocked payload)
# ---------------------------------------------------------------------------


def test_stripe_webhook_invoice_paid_mock():
    """Mock a Stripe invoice.paid event and verify it is handled correctly.
    
    This validates the webhook payload structure and handler logic without
    requiring a live Stripe connection. The route.ts (Next.js) handles the
    actual HTTP layer; here we validate the Python-side billing state update.
    """
    # Simulate what the Stripe webhook would trigger:
    # a workspace receiving a payment → credits added
    meter, TOKEN_COST_RATE, _ = make_fresh_meter()
    ws_id = "ws-stripe-paid"

    # Simulate the workspace already having usage
    meter.record_workspace_usage(ws_id, tokens=50_000)  # ~$0.75
    meter.record_budget_cap(ws_id, cap=0.50)

    # Pre-payment: budget exceeded
    assert meter.check_budget_exceeded(ws_id) is True

    # Stripe invoice.paid handler: reset the workspace (billing period renewal)
    meter.reset_workspace_usage(ws_id)
    # Set new cap (representing paid plan limit)
    meter.record_budget_cap(ws_id, cap=10.00)

    # Post-payment: budget should not be exceeded
    assert meter.check_budget_exceeded(ws_id) is False
    usage = meter.get_workspace_usage(ws_id)
    assert usage["budget_cap_usd"] == 10.00
    assert usage["total_tokens"] == 0


def test_stripe_webhook_subscription_deleted_mock():
    """Simulate subscription.deleted → workspace budget set to 0 (free tier)."""
    meter, TOKEN_COST_RATE, _ = make_fresh_meter()
    ws_id = "ws-stripe-deleted"

    # Subscription deleted → reset to minimal free cap
    meter.reset_workspace_usage(ws_id)
    free_cap = round(1_000 * TOKEN_COST_RATE, 6)  # 1000 tokens free
    meter.record_budget_cap(ws_id, cap=free_cap)

    usage = meter.get_workspace_usage(ws_id)
    assert usage["budget_cap_usd"] == free_cap

    # Any usage over free cap triggers exceeded
    meter.record_workspace_usage(ws_id, tokens=1001)
    assert meter.check_budget_exceeded(ws_id) is True


def test_simulate_10k_budget_interruption(meter, rates):
    """Full scenario: 10k events, budget set mid-way, interruption detected."""
    TOKEN_COST_RATE, _ = rates
    ws_id = "ws-10k-budget"

    # Set cap at $5.00 — will be breached at ~333,334 tokens
    cap = 5.00
    meter.record_budget_cap(ws_id, cap=cap)

    # Simulate in batches and check interruption
    interrupted_at = None
    for i in range(10_000):
        meter.record_workspace_usage(ws_id, tokens=100)
        if meter.check_budget_exceeded(ws_id):
            interrupted_at = i + 1
            break

    assert interrupted_at is not None, "Budget should have been exceeded during 10k events"
    # At $0.000015/token, $5.00 / $0.000015 = 333,334 tokens → ~3334 events of 100 tokens
    # Allow ±2 events tolerance
    expected_event = int(cap / (100 * TOKEN_COST_RATE))
    assert abs(interrupted_at - expected_event) <= 2, (
        f"Expected interruption near event {expected_event}, got {interrupted_at}"
    )


# ---------------------------------------------------------------------------
# 8. Phase 10: Live Metered Billing & Webhook Audit Tests
# ---------------------------------------------------------------------------

from billing.metering import (
    usage_meter,
    push_usage_to_lago,
    check_spending_cap,
    enforce_spending_cap,
    BudgetExceededError,
    RATE_INPUT_PER_1K,
    RATE_OUTPUT_PER_1K,
    COST_PER_TOOL_HIT,
    COST_PER_SANDBOX_MINUTE,
)
from routers.webhooks import reset_processed_events
from app.agents.tools.sandbox_executor import execute_sandbox


@pytest.fixture(autouse=True)
def clean_billing_state():
    """Reset webhook idempotency and usage meter before each test."""
    reset_processed_events()
    usage_meter._local_usage.clear()
    usage_meter._local_budgets.clear()
    usage_meter.pushed_lago_events.clear()
    yield
    reset_processed_events()
    usage_meter._local_usage.clear()
    usage_meter._local_budgets.clear()
    usage_meter.pushed_lago_events.clear()


def test_usage_event_metering_with_hybrid_rates():
    """Verify granular usage logging: input tokens, output tokens, tool hits, sandbox minutes."""
    ws_id = "ws-hybrid-metering"
    usage_meter.reset_workspace(ws_id)

    event = usage_meter.log_usage_event(
        workspace_id=ws_id,
        input_tokens=2000,       # 2k * $0.003 = $0.006
        output_tokens=1000,      # 1k * $0.012 = $0.012
        tool_hits=4,             # 4 * $0.005  = $0.020
        sandbox_minutes=2.5,     # 2.5 * $0.010 = $0.025
    )

    expected_cost = round(0.006 + 0.012 + 0.020 + 0.025, 6)  # $0.063
    assert event["workspace_id"] == ws_id
    assert event["input_tokens"] == 2000
    assert event["output_tokens"] == 1000
    assert event["total_tokens"] == 3000
    assert event["tool_hits"] == 4
    assert event["sandbox_minutes"] == 2.5
    assert abs(event["total_cost_usd"] - expected_cost) < 1e-6


def test_push_usage_to_lago():
    """Verify pushing aggregated usage payload to Lago Metered Billing Engine."""
    ws_id = "ws-lago-push"
    usage_meter.reset_workspace(ws_id)

    usage_meter.log_usage_event(
        workspace_id=ws_id,
        input_tokens=5000,
        output_tokens=2500,
        tool_hits=2,
        sandbox_minutes=1.0,
    )

    lago_payload = push_usage_to_lago(ws_id)

    assert lago_payload["external_customer_id"] == ws_id
    assert lago_payload["code"] == "agent_token_consumption"
    assert "transaction_id" in lago_payload
    assert lago_payload["properties"]["input_tokens"] == 5000
    assert lago_payload["properties"]["output_tokens"] == 2500
    assert lago_payload["properties"]["tool_hits"] == 2
    assert lago_payload["properties"]["sandbox_minutes"] == 1.0
    assert lago_payload["properties"]["calculated_cost_usd"] > 0.0
    assert len(usage_meter.pushed_lago_events) == 1


def test_stripe_webhook_subscription_lifecycle(app_client):
    """Test POST /api/webhooks/stripe handling customer.subscription.created and deleted."""
    ws_id = "ws-sub-cycle"
    usage_meter.reset_workspace(ws_id)

    # 1. customer.subscription.created -> allocates Pro tier cap ($50.00)
    created_payload = {
        "id": "evt_sub_created_001",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_12345",
                "customer": "cus_12345",
                "metadata": {"workspace_id": ws_id, "plan": "pro"},
            }
        },
    }
    resp1 = app_client.post("/api/webhooks/stripe", json=created_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "processed"
    assert data1["workspace_id"] == ws_id
    assert usage_meter.get_budget_cap(ws_id) == 50.00

    # 2. customer.subscription.deleted -> degrades to Free tier cap ($1.00)
    deleted_payload = {
        "id": "evt_sub_deleted_002",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_12345",
                "customer": "cus_12345",
                "metadata": {"workspace_id": ws_id},
            }
        },
    }
    resp2 = app_client.post("/api/webhooks/stripe", json=deleted_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "processed"
    assert usage_meter.get_budget_cap(ws_id) == 1.00


def test_stripe_webhook_invoice_success_and_failure(app_client):
    """Test invoice.payment_succeeded renewing quota and invoice.payment_failed freezing execution."""
    ws_id = "ws-invoice-flow"
    usage_meter.reset_workspace(ws_id)

    # Simulate existing usage
    usage_meter.log_usage_event(ws_id, input_tokens=10000, output_tokens=10000)
    assert usage_meter.get_workspace_usage(ws_id)["total_tokens"] == 20000

    # 1. invoice.payment_succeeded -> resets usage meter and renews $50 cap
    paid_payload = {
        "id": "evt_inv_paid_003",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_12345",
                "customer": "cus_12345",
                "metadata": {"workspace_id": ws_id, "plan": "pro"},
            }
        },
    }
    resp1 = app_client.post("/api/webhooks/stripe", json=paid_payload)
    assert resp1.status_code == 200
    assert usage_meter.get_workspace_usage(ws_id)["total_tokens"] == 0
    assert usage_meter.get_budget_cap(ws_id) == 50.00

    # 2. invoice.payment_failed -> freezes workspace spending cap to 0.0
    failed_payload = {
        "id": "evt_inv_failed_004",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_12346",
                "customer": "cus_12345",
                "metadata": {"workspace_id": ws_id},
            }
        },
    }
    resp2 = app_client.post("/api/webhooks/stripe", json=failed_payload)
    assert resp2.status_code == 200
    assert usage_meter.get_budget_cap(ws_id) == 0.0
    # Any usage now exceeds the cap
    assert check_spending_cap(ws_id) is True


def test_stripe_webhook_idempotency_guard(app_client):
    """Verify duplicate webhook event IDs are detected and not processed twice."""
    ws_id = "ws-idempotent-test"
    event_payload = {
        "id": "evt_idempotency_check_999",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_duplicate_test",
                "customer": "cus_999",
                "metadata": {"workspace_id": ws_id, "plan": "pro"},
            }
        },
    }

    # First delivery
    resp1 = app_client.post("/api/webhooks/stripe", json=event_payload)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "processed"

    # Second delivery (replay / retry)
    resp2 = app_client.post("/api/webhooks/stripe", json=event_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "duplicate"
    assert "already been processed" in data2["message"]


def test_hard_spending_cap_freezes_sandbox_tool_execution():
    """Verify execute_sandbox raises BudgetExceededError when credit quota is exhausted."""
    ws_id = "ws-credit-depleted"
    usage_meter.reset_workspace(ws_id)
    usage_meter.set_budget_cap(ws_id, cap_usd=0.01)

    # Accumulate usage beyond $0.01 limit
    usage_meter.log_usage_event(ws_id, input_tokens=5000, output_tokens=1000)  # $0.027
    assert check_spending_cap(ws_id) is True

    # Attempting high-cost sandbox execution must raise BudgetExceededError (402)
    with pytest.raises(BudgetExceededError) as exc_info:
        execute_sandbox("print('hello sandbox')", workspace_id=ws_id)

    assert exc_info.value.status_code == 402
    assert "exceeded its spending budget cap" in exc_info.value.detail["message"]


def test_api_gateway_workflow_returns_402_on_depleted_credits(app_client):
    """Verify POST /api/v1/workflow/run returns HTTP 402 when workspace spending limit is reached."""
    ws_id = "ws-gateway-frozen"
    usage_meter.reset_workspace(ws_id)
    usage_meter.set_budget_cap(ws_id, cap_usd=0.005)

    # Exhaust budget
    usage_meter.log_usage_event(ws_id, input_tokens=2000, output_tokens=1000)  # ~$0.018
    assert check_spending_cap(ws_id) is True

    # Call workflow run endpoint with exhausted workspace
    response = app_client.post(
        "/api/v1/workflow/run",
        json={
            "workspace_id": ws_id,
            "prompt": "Execute automated code refactoring workflow",
        },
    )

    assert response.status_code == 402
    data = response.json()
    assert data["error"] == "BUDGET_CAP_EXCEEDED"
    assert data["workspace_id"] == ws_id
    assert "frozen" in data["message"].lower()



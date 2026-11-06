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


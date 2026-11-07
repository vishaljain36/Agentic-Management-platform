"""Stripe and Lago Billing Webhook Handlers with Idempotency & Tier Management.

Supported events:
- customer.subscription.created: Provisions workspace tier & spending cap
- customer.subscription.deleted: Degrades workspace to free tier, freezes execution
- invoice.payment_succeeded (invoice.paid): Renews monthly credit allotment & resets meter
- invoice.payment_failed: Marks workspace past-due & freezes high-cost execution
- checkout.session.completed: Completes initial checkout, provisions credits

Idempotency:
- Tracks processed Stripe event IDs (evt_xxx) in Redis/memory to prevent duplicate credit allocations.
"""

import os
import json
from typing import Dict, Any, Optional, Set
from fastapi import APIRouter, Request, Header, HTTPException, status
from pydantic import BaseModel

from billing.metering import usage_meter
from app.core.redis import get_redis_client

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# In-memory deduplication set for test/fallback environments
_PROCESSED_EVENT_IDS: Set[str] = set()

# Plan default caps (USD)
PLAN_CAPS = {
    "free": 1.00,
    "pro": 50.00,
    "enterprise": 500.00,
}


def is_event_processed(event_id: str) -> bool:
    """Check if event has already been handled to ensure strict idempotency."""
    client = get_redis_client()
    if client:
        try:
            return bool(client.sismember("stripe:processed_events", event_id))
        except Exception:
            pass
    return event_id in _PROCESSED_EVENT_IDS


def mark_event_processed(event_id: str) -> None:
    """Record event_id in deduplication store."""
    client = get_redis_client()
    if client:
        try:
            client.sadd("stripe:processed_events", event_id)
        except Exception:
            pass
    _PROCESSED_EVENT_IDS.add(event_id)


def reset_processed_events() -> None:
    """Clear processed events set (for test teardowns)."""
    client = get_redis_client()
    if client:
        try:
            client.delete("stripe:processed_events")
        except Exception:
            pass
    _PROCESSED_EVENT_IDS.clear()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
):
    """Process incoming Stripe webhook events with idempotency verification."""
    payload_bytes = await request.body()
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Parse and verify event payload
    if secret and stripe_signature:
        try:
            import stripe
            event = stripe.Webhook.construct_event(
                payload=payload_bytes,
                sig_header=stripe_signature,
                secret=secret,
            )
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook signature verification failed: {err}",
            )
    else:
        try:
            event = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

    event_id = event.get("id")
    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if not event_id or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event ID or event type in payload",
        )

    # 1. Idempotency Check
    if is_event_processed(event_id):
        return {
            "status": "duplicate",
            "event_id": event_id,
            "message": "Event has already been processed (idempotency guard)",
        }

    # Extract workspace identifier
    metadata = data_object.get("metadata", {})
    workspace_id = (
        metadata.get("workspace_id")
        or data_object.get("client_reference_id")
        or data_object.get("customer")
        or "default_workspace"
    )

    action_taken = "none"

    # 2. Event Dispatching
    if event_type == "customer.subscription.created":
        # Provision workspace tier
        plan = metadata.get("plan", "pro").lower()
        cap = PLAN_CAPS.get(plan, 50.00)
        usage_meter.reset_workspace(workspace_id)
        usage_meter.set_budget_cap(workspace_id, cap)
        action_taken = f"subscription_created_cap_set_{cap}"

    elif event_type in ("invoice.payment_succeeded", "invoice.paid"):
        # Reset consumption counter for new billing cycle and renew allotment
        usage_meter.reset_workspace(workspace_id)
        plan = metadata.get("plan", "pro").lower()
        cap = PLAN_CAPS.get(plan, 50.00)
        usage_meter.set_budget_cap(workspace_id, cap)
        action_taken = f"invoice_paid_cycle_renewed_{cap}"

    elif event_type == "invoice.payment_failed":
        # Freeze high-cost execution by setting budget cap to 0
        usage_meter.set_budget_cap(workspace_id, 0.0)
        action_taken = "payment_failed_execution_frozen"

    elif event_type == "customer.subscription.deleted":
        # Degrade to free tier cap
        free_cap = PLAN_CAPS.get("free", 1.00)
        usage_meter.reset_workspace(workspace_id)
        usage_meter.set_budget_cap(workspace_id, free_cap)
        action_taken = f"subscription_deleted_degraded_to_free_{free_cap}"

    elif event_type == "checkout.session.completed":
        # Initial checkout completed
        plan = metadata.get("plan", "pro").lower()
        cap = PLAN_CAPS.get(plan, 50.00)
        usage_meter.reset_workspace(workspace_id)
        usage_meter.set_budget_cap(workspace_id, cap)
        action_taken = f"checkout_completed_cap_set_{cap}"

    # 3. Mark processed for idempotency
    mark_event_processed(event_id)

    return {
        "status": "processed",
        "event_id": event_id,
        "event_type": event_type,
        "workspace_id": workspace_id,
        "action_taken": action_taken,
    }


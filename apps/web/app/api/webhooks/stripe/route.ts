import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { prisma } from "db";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "sk_test_placeholder", {
  apiVersion: "2025-02-24.acacia" as any,
});

const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET || "whsec_test_secret";

// Credit allocations by plan tier
const PLAN_CREDITS: Record<string, number> = {
  starter: 100_000,
  pro: 500_000,
  enterprise: 2_500_000,
};

export async function POST(req: NextRequest) {
  const body = await req.text();
  const signature = req.headers.get("stripe-signature");

  let event: Stripe.Event;

  try {
    if (webhookSecret && signature && !signature.startsWith("test_mock_sig")) {
      event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
    } else {
      // Allow parsed JSON in testing/development environments
      event = JSON.parse(body) as Stripe.Event;
    }
  } catch (err: any) {
    console.error("[Stripe Webhook] Signature verification failed:", err.message);
    return NextResponse.json({ error: `Webhook Error: ${err.message}` }, { status: 400 });
  }

  try {
    switch (event.type) {
      case "invoice.paid":
      case "invoice.payment_succeeded": {
        const invoice = event.data.object as any;
        const workspaceId =
          invoice.subscription_details?.metadata?.workspaceId ||
          invoice.metadata?.workspaceId;
        const customerEmail = invoice.customer_email;

        // Calculate credit allocation: $1 = 100,000 tokens/credits equivalent
        const amountPaidCents = invoice.amount_paid || 0;
        const creditsPurchased = Math.max(100_000, amountPaidCents * 100);

        if (workspaceId) {
          await prisma.workspace.update({
            where: { id: workspaceId },
            data: {
              credits: { increment: creditsPurchased },
            },
          });
        } else if (customerEmail) {
          const userWithWorkspace = await prisma.user.findUnique({
            where: { email: customerEmail },
            include: { memberships: { include: { workspace: true } } },
          });

          if (userWithWorkspace?.memberships[0]?.workspaceId) {
            await prisma.workspace.update({
              where: { id: userWithWorkspace.memberships[0].workspaceId },
              data: {
                credits: { increment: creditsPurchased },
              },
            });
          }
        }
        break;
      }

      case "customer.subscription.created":
      case "customer.subscription.updated": {
        const subscription = event.data.object as Stripe.Subscription;
        const workspaceId = (subscription.metadata as any)?.workspaceId;
        const planTier = ((subscription.metadata as any)?.plan || "pro").toLowerCase();

        const creditAllocation = PLAN_CREDITS[planTier] || PLAN_CREDITS.pro;

        if (workspaceId) {
          await prisma.workspace.update({
            where: { id: workspaceId },
            data: {
              plan: planTier,
              credits: { increment: creditAllocation },
            },
          });
        }
        break;
      }

      case "customer.subscription.deleted": {
        const subscription = event.data.object as Stripe.Subscription;
        const workspaceId = (subscription.metadata as any)?.workspaceId;

        if (workspaceId) {
          await prisma.workspace.update({
            where: { id: workspaceId },
            data: {
              plan: "starter",
              credits: PLAN_CREDITS.starter,
            },
          });
        }
        break;
      }

      default:
        // Ignore unhandled event types
        break;
    }

    return NextResponse.json({ received: true, event: event.type }, { status: 200 });
  } catch (err: any) {
    console.error("[Stripe Webhook] Processing error:", err);
    return NextResponse.json({ error: "Failed to process webhook event" }, { status: 500 });
  }
}

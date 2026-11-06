import { NextRequest, NextResponse } from "next/server";
import { prisma } from "db";

// Lago webhook event handler for usage and subscriptions
export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const eventType = payload.webhook_type || payload.event_type;
    const data = payload.data || payload;

    switch (eventType) {
      case "invoice.created":
      case "invoice.paid": {
        const externalCustomerId = data.customer?.external_id;
        const totalAmount = data.total_amount_cents || 0;
        const credits = Math.max(50_000, totalAmount * 100);

        if (externalCustomerId) {
          await prisma.workspace.updateMany({
            where: { id: externalCustomerId },
            data: {
              credits: { increment: credits },
            },
          });
        }
        break;
      }

      case "subscription.started":
      case "subscription.upgraded": {
        const externalCustomerId = data.customer?.external_id;
        const planCode = data.subscription?.plan_code || "pro";

        if (externalCustomerId) {
          await prisma.workspace.updateMany({
            where: { id: externalCustomerId },
            data: {
              plan: planCode.toLowerCase(),
            },
          });
        }
        break;
      }

      case "subscription.terminated": {
        const externalCustomerId = data.customer?.external_id;
        if (externalCustomerId) {
          await prisma.workspace.updateMany({
            where: { id: externalCustomerId },
            data: {
              plan: "starter",
            },
          });
        }
        break;
      }

      default:
        break;
    }

    return NextResponse.json({ received: true, event: eventType }, { status: 200 });
  } catch (err: any) {
    console.error("[Lago Webhook] Error:", err);
    return NextResponse.json({ error: "Failed to process Lago webhook" }, { status: 500 });
  }
}


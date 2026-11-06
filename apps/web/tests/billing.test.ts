import { describe, it, expect, vi, beforeEach } from "vitest";
import { POST as stripeWebhookHandler } from "@/app/api/webhooks/stripe/route";
import { POST as lagoWebhookHandler } from "@/app/api/webhooks/lago/route";
import { formatTokens, formatUsd } from "@/lib/utils";
import { NextRequest } from "next/server";

// Mock Prisma
vi.mock("db", () => {
  return {
    prisma: {
      workspace: {
        update: vi.fn().mockResolvedValue({ id: "ws-mock-id", credits: 200000 }),
        updateMany: vi.fn().mockResolvedValue({ count: 1 }),
      },
      user: {
        findUnique: vi.fn().mockResolvedValue({
          id: "usr-1",
          email: "customer@example.com",
          memberships: [{ workspaceId: "ws-mock-id" }],
        }),
      },
    },
  };
});

describe("Phase 5 — Billing, Metering & Webhooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Utility Formatters & Cost Formula", () => {
    it("formats token numbers with compact notation", () => {
      expect(formatTokens(950)).toBe("950");
      expect(formatTokens(1_500)).toBe("1.5k");
      expect(formatTokens(2_400_000)).toBe("2.4M");
    });

    it("formats USD currency values accurately", () => {
      expect(formatUsd(0.00015)).toBe("$0.000150");
      expect(formatUsd(12.5)).toBe("$12.50");
      expect(formatUsd(1250.75)).toBe("$1,250.75");
    });
  });

  describe("Stripe Webhook Handler", () => {
    it("handles invoice.paid and credits workspace", async () => {
      const payload = {
        type: "invoice.paid",
        data: {
          object: {
            id: "in_mock_123",
            amount_paid: 2000, // $20.00
            customer_email: "customer@example.com",
            subscription_details: {
              metadata: {
                workspaceId: "ws-test-123",
              },
            },
          },
        },
      };

      const req = new NextRequest("http://localhost:3000/api/webhooks/stripe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "stripe-signature": "test_mock_sig",
        },
        body: JSON.stringify(payload),
      });

      const response = await stripeWebhookHandler(req);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.received).toBe(true);
      expect(data.event).toBe("invoice.paid");

      const { prisma } = await import("db");
      expect(prisma.workspace.update).toHaveBeenCalledWith({
        where: { id: "ws-test-123" },
        data: {
          credits: { increment: 200000 },
        },
      });
    });

    it("handles customer.subscription.updated and sets plan tier", async () => {
      const payload = {
        type: "customer.subscription.updated",
        data: {
          object: {
            id: "sub_mock_123",
            metadata: {
              workspaceId: "ws-test-123",
              plan: "enterprise",
            },
          },
        },
      };

      const req = new NextRequest("http://localhost:3000/api/webhooks/stripe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "stripe-signature": "test_mock_sig",
        },
        body: JSON.stringify(payload),
      });

      const response = await stripeWebhookHandler(req);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.received).toBe(true);

      const { prisma } = await import("db");
      expect(prisma.workspace.update).toHaveBeenCalledWith({
        where: { id: "ws-test-123" },
        data: {
          plan: "enterprise",
          credits: { increment: 2_500_000 },
        },
      });
    });

    it("handles customer.subscription.deleted by downgrading to starter", async () => {
      const payload = {
        type: "customer.subscription.deleted",
        data: {
          object: {
            id: "sub_mock_123",
            metadata: {
              workspaceId: "ws-test-123",
            },
          },
        },
      };

      const req = new NextRequest("http://localhost:3000/api/webhooks/stripe", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "stripe-signature": "test_mock_sig",
        },
        body: JSON.stringify(payload),
      });

      const response = await stripeWebhookHandler(req);
      expect(response.status).toBe(200);

      const { prisma } = await import("db");
      expect(prisma.workspace.update).toHaveBeenCalledWith({
        where: { id: "ws-test-123" },
        data: {
          plan: "starter",
          credits: 100_000,
        },
      });
    });
  });

  describe("Lago Webhook Handler", () => {
    it("handles invoice.paid from Lago", async () => {
      const payload = {
        webhook_type: "invoice.paid",
        data: {
          customer: { external_id: "ws-lago-123" },
          total_amount_cents: 1500,
        },
      };

      const req = new NextRequest("http://localhost:3000/api/webhooks/lago", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const response = await lagoWebhookHandler(req);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.received).toBe(true);
      expect(data.event).toBe("invoice.paid");

      const { prisma } = await import("db");
      expect(prisma.workspace.updateMany).toHaveBeenCalledWith({
        where: { id: "ws-lago-123" },
        data: { credits: { increment: 150000 } },
      });
    });
  });
});


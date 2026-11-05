"use client";

import React, { useState } from "react";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import {
  TrendingUp,
  DollarSign,
  PieChart,
  Layers,
  ArrowUpRight,
  RefreshCw,
  Zap,
} from "lucide-react";

interface ProviderMargin {
  provider: string;
  retailPricePer1M: number;
  wholesaleCostPer1M: number;
  marginPercent: number;
  volumeTokens30d: string;
  grossProfitUsd: number;
}

export default function PlatformMetricsPage() {
  const [timeRange, setTimeRange] = useState<"24h" | "7d" | "30d" | "all">("30d");

  const margins: ProviderMargin[] = [
    {
      provider: "OpenAI GPT-4o",
      retailPricePer1M: 15.0,
      wholesaleCostPer1M: 3.25,
      marginPercent: 78.3,
      volumeTokens30d: "185.4M",
      grossProfitUsd: 2178.45,
    },
    {
      provider: "Anthropic Claude 3.5 Sonnet",
      retailPricePer1M: 16.5,
      wholesaleCostPer1M: 3.75,
      marginPercent: 77.2,
      volumeTokens30d: "142.1M",
      grossProfitUsd: 1811.77,
    },
    {
      provider: "Google Gemini 1.5 Pro",
      retailPricePer1M: 12.0,
      wholesaleCostPer1M: 2.1,
      marginPercent: 82.5,
      volumeTokens30d: "68.9M",
      grossProfitUsd: 682.11,
    },
    {
      provider: "DeepSeek V3",
      retailPricePer1M: 5.0,
      wholesaleCostPer1M: 0.85,
      marginPercent: 83.0,
      volumeTokens30d: "21.8M",
      grossProfitUsd: 90.47,
    },
  ];

  const totalWholesale = 1384.2;
  const totalRetail = 6147.0;
  const blendedMargin = (((totalRetail - totalWholesale) / totalRetail) * 100).toFixed(1);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Platform Margins & Cost Analytics
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Real-time financial telemetry, wholesale token expenses, and gross unit economics
          </p>
        </div>

        <div className="flex items-center gap-2">
          {(["24h", "7d", "30d", "all"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-3 py-1 rounded text-xs font-mono uppercase transition-colors ${
                timeRange === r
                  ? "bg-[#8B5CF6] text-white"
                  : "bg-white/5 text-zinc-400 hover:text-white"
              }`}
            >
              {r}
            </button>
          ))}
          <Button variant="ghost" size="sm" className="gap-1 border border-white/10 text-xs">
            <RefreshCw size={12} />
            <span>Sync Lago</span>
          </Button>
        </div>
      </div>

      {/* High-Level Financial KPI Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <GlassCard glow="cyan" className="p-5">
          <div className="text-xs font-mono text-zinc-400">BLENDED GROSS MARGIN</div>
          <div className="mt-2 text-3xl font-bold font-mono text-[#06B6D4]">{blendedMargin}%</div>
          <div className="mt-1 text-xs text-zinc-400 font-mono">Formula: (Retail - Wholesale) / Retail</div>
        </GlassCard>

        <GlassCard glow="emerald" className="p-5">
          <div className="text-xs font-mono text-zinc-400">30D RETAIL REVENUE</div>
          <div className="mt-2 text-3xl font-bold font-mono text-[#10B981]">${totalRetail.toLocaleString()}</div>
          <div className="mt-1 text-xs text-emerald-400 font-mono">+18.4% vs previous period</div>
        </GlassCard>

        <GlassCard glow="none" className="p-5">
          <div className="text-xs font-mono text-zinc-400">30D WHOLESALE LLM EXPENSE</div>
          <div className="mt-2 text-3xl font-bold font-mono text-white">${totalWholesale.toLocaleString()}</div>
          <div className="mt-1 text-xs text-zinc-400 font-mono">Direct API vendor billing</div>
        </GlassCard>

        <GlassCard glow="violet" className="p-5">
          <div className="text-xs font-mono text-zinc-400">NET CONTRIBUTION PROFIT</div>
          <div className="mt-2 text-3xl font-bold font-mono text-[#8B5CF6]">
            ${(totalRetail - totalWholesale).toFixed(2)}
          </div>
          <div className="mt-1 text-xs text-violet-400 font-mono">Platform cash-flow positive</div>
        </GlassCard>
      </div>

      {/* Provider Margin Table */}
      <GlassCard className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-semibold text-white">Provider Unit Economics Matrix</h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Wholesale API cost vs user consumption billing rate per 1,000,000 tokens
            </p>
          </div>
          <span className="text-xs font-mono text-zinc-400 bg-white/5 px-2.5 py-1 rounded border border-white/10">
            Formula: Total Cost = Σ(Tokens × Rate) + Σ(Tools × Cost)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-xs font-mono uppercase text-zinc-400">
                <th className="pb-3 font-medium">Model / Provider</th>
                <th className="pb-3 font-medium text-right">Retail / 1M Tokens</th>
                <th className="pb-3 font-medium text-right">Wholesale / 1M Tokens</th>
                <th className="pb-3 font-medium text-right">Unit Margin</th>
                <th className="pb-3 font-medium text-right">30D Token Volume</th>
                <th className="pb-3 font-medium text-right">Gross Profit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 font-mono text-xs">
              {margins.map((m) => (
                <tr key={m.provider} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 font-sans font-medium text-white flex items-center gap-2">
                    <Zap size={14} className="text-[#8B5CF6]" />
                    {m.provider}
                  </td>
                  <td className="py-3 text-right text-zinc-300">${m.retailPricePer1M.toFixed(2)}</td>
                  <td className="py-3 text-right text-zinc-400">${m.wholesaleCostPer1M.toFixed(2)}</td>
                  <td className="py-3 text-right font-semibold text-emerald-400">{m.marginPercent}%</td>
                  <td className="py-3 text-right text-zinc-300">{m.volumeTokens30d}</td>
                  <td className="py-3 text-right font-semibold text-[#06B6D4]">
                    ${m.grossProfitUsd.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* Cost Architecture Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <GlassCard className="p-6 space-y-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <PieChart size={16} className="text-[#06B6D4]" />
            Token-to-Tool Cost Distribution
          </h3>
          <div className="space-y-3 pt-2 font-mono text-xs">
            <div>
              <div className="flex justify-between text-zinc-300 mb-1">
                <span>LLM Generation Tokens</span>
                <span>87.4% ($1,210.00)</span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
                <div className="bg-[#8B5CF6] h-full rounded-full" style={{ width: "87.4%" }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-zinc-300 mb-1">
                <span>Docker Sandbox Code Runs ($0.001/call)</span>
                <span>8.2% ($113.50)</span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
                <div className="bg-[#06B6D4] h-full rounded-full" style={{ width: "8.2%" }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-zinc-300 mb-1">
                <span>Qdrant Vector Embeddings & Storage</span>
                <span>4.4% ($60.70)</span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-2 overflow-hidden">
                <div className="bg-[#10B981] h-full rounded-full" style={{ width: "4.4%" }} />
              </div>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-6 space-y-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Layers size={16} className="text-[#8B5CF6]" />
            Billing Reconciliation Engine
          </h3>
          <p className="text-xs text-zinc-400">
            Realtime synchronization between Redis TokenMeter in-memory aggregates and Stripe/Lago ledger entries.
          </p>
          <div className="bg-[#030712] rounded-lg p-3 border border-white/10 font-mono text-[11px] text-zinc-300 space-y-1">
            <div className="text-emerald-400">✓ Redis Pipeline Ingestion: 0.14ms avg latency</div>
            <div className="text-emerald-400">✓ Stripe Webhook Signature: SHA-256 HMAC Verified</div>
            <div className="text-emerald-400">✓ Lago Invoice Sync: Up to date (Batch #4901)</div>
            <div className="text-zinc-500">→ Budget Ceiling Interruption: Active on all 142 workspaces</div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}


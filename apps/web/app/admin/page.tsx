import React from "react";
import Link from "next/link";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import {
  BarChart3,
  Cpu,
  Users,
  TrendingUp,
  Activity,
  DollarSign,
  AlertTriangle,
  ArrowUpRight,
  ShieldCheck,
} from "lucide-react";

export default function AdminOverviewPage() {
  return (
    <div className="space-y-8">
      {/* Title & Banner */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Super Admin Control Tower
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Global telemetry, revenue margins, provider fallbacks, and multi-tenant security
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-xs font-mono text-emerald-400">All Clusters Operational</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <GlassCard glow="cyan" className="p-5">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-mono">
            <span>PLATFORM GROSS MARGIN</span>
            <TrendingUp size={16} className="text-[#06B6D4]" />
          </div>
          <div className="mt-3 text-3xl font-bold font-mono text-white">76.8%</div>
          <p className="text-xs text-emerald-400 mt-1 font-mono">+4.2% vs last month</p>
        </GlassCard>

        <GlassCard glow="violet" className="p-5">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-mono">
            <span>30-DAY TOKEN BURN</span>
            <Activity size={16} className="text-[#8B5CF6]" />
          </div>
          <div className="mt-3 text-3xl font-bold font-mono text-white">418.2M</div>
          <p className="text-xs text-zinc-400 mt-1 font-mono">Avg $0.000015 / token</p>
        </GlassCard>

        <GlassCard glow="emerald" className="p-5">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-mono">
            <span>ACTIVE TENANTS</span>
            <Users size={16} className="text-[#10B981]" />
          </div>
          <div className="mt-3 text-3xl font-bold font-mono text-white">142</div>
          <p className="text-xs text-emerald-400 mt-1 font-mono">98.6% quota adherence</p>
        </GlassCard>

        <GlassCard glow="none" className="p-5">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-mono">
            <span>CIRCUIT BREAKER STATUS</span>
            <ShieldCheck size={16} className="text-emerald-400" />
          </div>
          <div className="mt-3 text-3xl font-bold font-mono text-emerald-400">NORMAL</div>
          <p className="text-xs text-zinc-400 mt-1 font-mono">4 LLM fallbacks standby</p>
        </GlassCard>
      </div>

      {/* Navigation Sections */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard className="p-6 space-y-4">
          <div className="w-10 h-10 rounded-lg bg-[#06B6D4]/10 border border-[#06B6D4]/30 flex items-center justify-center text-[#06B6D4]">
            <BarChart3 size={20} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Platform Margins & Costs</h3>
            <p className="text-sm text-zinc-400 mt-1">
              Analyze token margins, wholesale LLM API spend vs retail customer pricing, and Lago/Stripe reconciliation.
            </p>
          </div>
          <Link href="/admin/metrics" className="inline-block pt-2">
            <Button variant="secondary" size="sm" className="gap-1.5">
              <span>View Financial Telemetry</span>
              <ArrowUpRight size={14} />
            </Button>
          </Link>
        </GlassCard>

        <GlassCard className="p-6 space-y-4">
          <div className="w-10 h-10 rounded-lg bg-[#8B5CF6]/10 border border-[#8B5CF6]/30 flex items-center justify-center text-[#8B5CF6]">
            <Cpu size={20} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">LLM Provider Fallbacks</h3>
            <p className="text-sm text-zinc-400 mt-1">
              Configure failover chains between OpenAI, Anthropic, Google Gemini, and DeepSeek with automated circuit breakers.
            </p>
          </div>
          <Link href="/admin/providers" className="inline-block pt-2">
            <Button variant="primary" size="sm" className="gap-1.5">
              <span>Configure Routing Chains</span>
              <ArrowUpRight size={14} />
            </Button>
          </Link>
        </GlassCard>

        <GlassCard className="p-6 space-y-4">
          <div className="w-10 h-10 rounded-lg bg-[#10B981]/10 border border-[#10B981]/30 flex items-center justify-center text-[#10B981]">
            <Users size={20} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">User & Quota Management</h3>
            <p className="text-sm text-zinc-400 mt-1">
              Manage multi-tenant permissions, allocate workspace credit pools, and revoke compromised API keys immediately.
            </p>
          </div>
          <Link href="/admin/users" className="inline-block pt-2">
            <Button variant="ghost" size="sm" className="border border-white/10 gap-1.5">
              <span>Manage User Directory</span>
              <ArrowUpRight size={14} />
            </Button>
          </Link>
        </GlassCard>
      </div>
    </div>
  );
}


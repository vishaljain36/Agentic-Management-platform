"use client";

import React, { useState } from "react";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import {
  Cpu,
  CheckCircle2,
  AlertTriangle,
  ArrowDown,
  RefreshCw,
  Power,
  Shield,
  Sliders,
} from "lucide-react";

interface ProviderConfig {
  id: string;
  name: string;
  priority: number;
  models: string[];
  status: "healthy" | "degraded" | "offline";
  latencyMs: number;
  circuitBreakerTripped: boolean;
  rateLimitTpm: number;
  failureRatePercent: number;
}

export default function ProvidersFallbackPage() {
  const [providers, setProviders] = useState<ProviderConfig[]>([
    {
      id: "openai",
      name: "OpenAI Primary Gateway",
      priority: 1,
      models: ["gpt-4o", "gpt-4o-mini", "o3-mini"],
      status: "healthy",
      latencyMs: 342,
      circuitBreakerTripped: false,
      rateLimitTpm: 2_000_000,
      failureRatePercent: 0.12,
    },
    {
      id: "anthropic",
      name: "Anthropic Secondary Fallback",
      priority: 2,
      models: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
      status: "healthy",
      latencyMs: 418,
      circuitBreakerTripped: false,
      rateLimitTpm: 1_000_000,
      failureRatePercent: 0.08,
    },
    {
      id: "google",
      name: "Google Gemini Tertiary Fallback",
      priority: 3,
      models: ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"],
      status: "healthy",
      latencyMs: 295,
      circuitBreakerTripped: false,
      rateLimitTpm: 4_000_000,
      failureRatePercent: 0.05,
    },
    {
      id: "deepseek",
      name: "DeepSeek Emergency Low-Cost Failover",
      priority: 4,
      models: ["deepseek-chat", "deepseek-coder", "deepseek-r1"],
      status: "healthy",
      latencyMs: 620,
      circuitBreakerTripped: false,
      rateLimitTpm: 500_000,
      failureRatePercent: 0.45,
    },
  ]);

  const toggleCircuitBreaker = (id: string) => {
    setProviders((prev) =>
      prev.map((p) =>
        p.id === id
          ? {
              ...p,
              circuitBreakerTripped: !p.circuitBreakerTripped,
              status: !p.circuitBreakerTripped ? "degraded" : "healthy",
            }
          : p
      )
    );
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            LLM Provider Fallback Router
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Dynamic failover cascade, circuit breaker thresholds, and upstream provider health
          </p>
        </div>

        <Button variant="secondary" size="sm" className="gap-1.5 font-mono text-xs">
          <RefreshCw size={12} />
          <span>Test Health Cascade</span>
        </Button>
      </div>

      {/* Failover Cascade Visual Hierarchy */}
      <div className="space-y-4">
        {providers.map((p, index) => (
          <React.Fragment key={p.id}>
            <GlassCard
              glow={p.circuitBreakerTripped ? "amber" : p.status === "healthy" ? "violet" : "none"}
              className="p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4"
            >
              <div className="flex items-center gap-4">
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-white/5 border border-white/10 font-mono font-bold text-sm text-[#8B5CF6]">
                  #{p.priority}
                </div>
                <div>
                  <div className="flex items-center gap-2.5">
                    <h3 className="text-base font-semibold text-white">{p.name}</h3>
                    {p.circuitBreakerTripped ? (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        CIRCUIT TRIPPED
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                        <CheckCircle2 size={10} />
                        HEALTHY
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {p.models.map((m) => (
                      <span
                        key={m}
                        className="text-[11px] font-mono px-2 py-0.5 rounded bg-white/5 text-zinc-300 border border-white/10"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Telemetry Numbers */}
              <div className="flex items-center gap-6 font-mono text-xs">
                <div>
                  <span className="text-zinc-500 block text-[10px]">AVG LATENCY</span>
                  <span className="text-zinc-200 font-semibold">{p.latencyMs} ms</span>
                </div>
                <div>
                  <span className="text-zinc-500 block text-[10px]">FAILURE RATE</span>
                  <span
                    className={
                      p.failureRatePercent > 0.2 ? "text-amber-400 font-semibold" : "text-emerald-400"
                    }
                  >
                    {p.failureRatePercent}%
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500 block text-[10px]">TPM CEILING</span>
                  <span className="text-zinc-300">{(p.rateLimitTpm / 1000).toFixed(0)}k</span>
                </div>

                {/* Circuit Breaker Toggle */}
                <Button
                  onClick={() => toggleCircuitBreaker(p.id)}
                  variant={p.circuitBreakerTripped ? "amber" : "ghost"}
                  size="sm"
                  className="gap-1.5 border border-white/10 text-xs"
                >
                  <Power size={12} />
                  <span>{p.circuitBreakerTripped ? "Reset Breaker" : "Trip Breaker"}</span>
                </Button>
              </div>
            </GlassCard>

            {index < providers.length - 1 && (
              <div className="flex items-center justify-center my-1">
                <div className="flex items-center gap-2 text-xs font-mono text-zinc-500 bg-[#0B0F19] px-3 py-1 rounded-full border border-white/5">
                  <ArrowDown size={12} className="text-[#8B5CF6]" />
                  <span>On HTTP 429 / 503 failover to Priority #{p.priority + 1}</span>
                </div>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Global Fallback Policy Controls */}
      <GlassCard className="p-6">
        <h2 className="text-base font-semibold text-white flex items-center gap-2 mb-2">
          <Shield size={16} className="text-[#06B6D4]" />
          Automated Circuit Breaker Policy
        </h2>
        <p className="text-xs text-zinc-400 mb-4">
          When an upstream provider exceeds failure or latency thresholds, traffic automatically shifts downstream within 50ms.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          <div className="p-3 rounded bg-white/5 border border-white/10">
            <span className="text-zinc-400 block text-[11px]">MAX RETRIES PER PROVIDER</span>
            <span className="text-white text-base font-bold">2 Attempts</span>
            <p className="text-[10px] text-zinc-500 mt-1">Exponential backoff (200ms, 400ms)</p>
          </div>
          <div className="p-3 rounded bg-white/5 border border-white/10">
            <span className="text-zinc-400 block text-[11px]">CIRCUIT BREAKER TRIGGER</span>
            <span className="text-white text-base font-bold">5% Failures in 60s</span>
            <p className="text-[10px] text-zinc-500 mt-1">Auto-isolates upstream for 120s cooldown</p>
          </div>
          <div className="p-3 rounded bg-white/5 border border-white/10">
            <span className="text-zinc-400 block text-[11px]">LATENCY SLA TIMEOUT</span>
            <span className="text-white text-base font-bold">4,000 ms</span>
            <p className="text-[10px] text-zinc-500 mt-1">Interrupts stalled stream and reroutes</p>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}


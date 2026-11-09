"use client";

import React from "react";
import Link from "next/link";
import { formatTokens } from "@/lib/utils";
import { AlertCircle, AlertTriangle, ArrowUpRight, Zap } from "lucide-react";

export interface UsageGaugeProps {
  usedCredits: number;
  totalCredits?: number;
  stripePortalUrl?: string;
  className?: string;
}

export const UsageGauge: React.FC<UsageGaugeProps> = ({
  usedCredits,
  totalCredits = 100000,
  stripePortalUrl = "https://billing.stripe.com/p/session_test",
  className = "",
}) => {
  const percentage = Math.min(
    100,
    Math.max(0, Math.round((usedCredits / totalCredits) * 100))
  );

  const isCritical = percentage >= 95;
  const isWarning = percentage >= 80 && !isCritical;

  let statusBadge = {
    label: "Normal",
    color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    barColor: "bg-emerald-500",
  };

  if (isCritical) {
    statusBadge = {
      label: "Critical",
      color: "bg-red-500/10 text-red-400 border-red-500/20",
      barColor: "bg-red-500",
    };
  } else if (isWarning) {
    statusBadge = {
      label: "Warning",
      color: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      barColor: "bg-amber-500",
    };
  }

  return (
    <div
      data-testid="usage-gauge"
      className={`rounded-xl border border-white/10 bg-[#0B0F19]/90 p-4 backdrop-blur-cyber ${className}`}
    >
      <div className="flex items-center justify-between pb-3">
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-[#8B5CF6]" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
            Monthly Credit Usage
          </h4>
        </div>
        <span
          data-testid="status-badge"
          className={`rounded border px-2 py-0.5 font-mono text-[11px] font-medium ${statusBadge.color}`}
        >
          {statusBadge.label}
        </span>
      </div>

      <div className="mb-2 flex items-baseline justify-between">
        <span className="font-mono text-xl font-bold text-white">
          {percentage}%
        </span>
        <span className="font-mono text-xs text-zinc-400">
          {formatTokens(usedCredits)} / {formatTokens(totalCredits)} Credits
        </span>
      </div>

      {/* Progress Bar Container */}
      <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
        <div
          data-testid="usage-progress-bar"
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
          className={`h-full transition-all duration-300 ${statusBadge.barColor}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Threshold Alerts & Upgrade Button */}
      {isWarning && (
        <div className="mt-3 flex items-center gap-1.5 text-xs text-amber-400">
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>Approaching plan capacity (80%+ consumed).</span>
        </div>
      )}

      {isCritical && (
        <div className="mt-3 flex items-center justify-between gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-2.5">
          <div className="flex items-center gap-1.5 text-xs text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="font-medium">Critical limit reached (95%+).</span>
          </div>
          <Link
            href={stripePortalUrl}
            data-testid="upgrade-plan-btn"
            className="flex items-center gap-1 rounded bg-red-500 px-2.5 py-1 text-xs font-medium text-white shadow-sm hover:bg-red-600 transition-colors"
          >
            Upgrade Plan
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      )}
    </div>
  );
};


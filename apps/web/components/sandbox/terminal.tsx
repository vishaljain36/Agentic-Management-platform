import React, { useState } from "react";
import { Terminal as TerminalIcon, FileText, Database, ShieldCheck } from "lucide-react";
import { formatTokens, formatUsd } from "@/lib/utils";
import { useAgentStore } from "@/store/use-agent-store";

export const SandboxTerminal: React.FC = () => {
  const { totalTokens, costUsd, status } = useAgentStore();
  const [activeTab, setActiveTab] = useState<"terminal" | "docs">("terminal");

  return (
    <div className="flex h-full flex-col rounded-xl border border-white/10 bg-[#0B0F19]/80 p-3.5 backdrop-blur-cyber">
      {/* Tabs */}
      <div className="mb-2.5 flex items-center justify-between border-b border-white/5 pb-2">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab("terminal")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
              activeTab === "terminal"
                ? "bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <TerminalIcon className="h-3.5 w-3.5" />
            Sandbox HUD
          </button>
          <button
            onClick={() => setActiveTab("docs")}
            className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
              activeTab === "docs"
                ? "bg-[#06B6D4]/20 text-[#06B6D4] border border-[#06B6D4]/30"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Database className="h-3.5 w-3.5" />
            Document Grounding
          </button>
        </div>

        {/* Telemetry pill */}
        <div className="flex items-center gap-2 font-mono text-[10px] text-zinc-400">
          <span>Tokens: <strong className="text-zinc-200">{formatTokens(totalTokens)}</strong></span>
          <span>Cost: <strong className="text-emerald-400">{formatUsd(costUsd)}</strong></span>
        </div>
      </div>

      {/* Tab Contents */}
      {activeTab === "terminal" ? (
        <div className="flex-1 space-y-2 font-mono text-[11px]">
          <div className="rounded-lg border border-white/5 bg-black/60 p-2.5">
            <div className="mb-1 text-zinc-500">// Environment Specifications</div>
            <div className="text-zinc-300">Container: <span className="text-[#10B981]">docker://python-sandbox:3.13-slim</span></div>
            <div className="text-zinc-300">Resource Bound: <span className="text-zinc-400">512MB RAM | 1 CPU</span></div>
            <div className="text-zinc-300">Network Isolation: <span className="text-[#06B6D4]">STRICT_LOCAL_ONLY</span></div>
            <div className="text-zinc-300">Timeout Cap: <span className="text-zinc-400">60 seconds</span></div>
          </div>

          <div className="rounded-lg border border-white/5 bg-black/60 p-2.5">
            <div className="mb-1 text-zinc-500">// Execution Status</div>
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-emerald-400" />
              <span className="text-zinc-200">Sandbox Ready (State: {status})</span>
            </div>
            <div className="mt-1 text-zinc-400">Security Gate: <span className="text-emerald-400">HITL AST Pre-Screen Active</span></div>
          </div>
        </div>
      ) : (
        <div className="flex-1 space-y-2 font-mono text-[11px]">
          <div className="rounded-lg border border-white/5 bg-black/60 p-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200 mb-1.5">
              <FileText className="h-4 w-4 text-[#06B6D4]" />
              Active Knowledge Base
            </div>
            <div className="text-zinc-400">Collection: <span className="text-[#06B6D4]">workspace_default</span></div>
            <div className="text-zinc-400">Embedding: <span className="text-zinc-200">BAAI/bge-small-en-v1.5 (384d)</span></div>
            <div className="text-zinc-400">Similarity Metric: <span className="text-zinc-200">COSINE</span></div>
          </div>

          <div className="rounded-lg border border-white/5 bg-black/60 p-2.5">
            <div className="text-zinc-500 mb-1">// Grounded Sources (Indexed)</div>
            <ul className="space-y-1 text-zinc-300">
              <li className="flex items-center gap-1.5">
                <ShieldCheck className="h-3 w-3 text-emerald-400" />
                <span>agentic_workspace_blueprint.md</span>
              </li>
              <li className="flex items-center gap-1.5">
                <ShieldCheck className="h-3 w-3 text-emerald-400" />
                <span>file_structure_specification.md</span>
              </li>
              <li className="flex items-center gap-1.5">
                <ShieldCheck className="h-3 w-3 text-emerald-400" />
                <span>product_requirements_document.md</span>
              </li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};


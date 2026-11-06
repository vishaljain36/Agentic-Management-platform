import React from "react";
import { useAgentStore } from "@/store/use-agent-store";
import { Terminal as TerminalIcon, Sparkles } from "lucide-react";

export const ThoughtTree: React.FC = () => {
  const { thoughtLogs, activeNode, status } = useAgentStore();

  return (
    <div className="flex h-full flex-col rounded-xl border border-white/10 bg-[#0B0F19]/80 p-3.5 backdrop-blur-cyber">
      <div className="mb-2.5 flex items-center justify-between border-b border-white/5 pb-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-300">
          <TerminalIcon className="h-4 w-4 text-[#8B5CF6]" />
          Agent Reasoning Tree & Traces
        </div>
        {activeNode && (
          <span className="flex items-center gap-1.5 rounded-full border border-[#8B5CF6]/30 bg-[#8B5CF6]/10 px-2 py-0.5 text-[10px] font-mono text-[#8B5CF6]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#8B5CF6] animate-ping" />
            {activeNode}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-1.5 font-mono text-[11px] text-zinc-300 pr-1">
        {thoughtLogs.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-xs text-zinc-500">
            Awaiting workflow initiation...
          </div>
        ) : (
          thoughtLogs.map((log, idx) => {
            const isError = log.includes("[ERROR]") || log.includes("[WARNING]");
            const isSuccess = log.includes("[SUCCESS]");
            const isHitl = log.includes("[HITL]");
            const isNode = log.includes("[NODE]");

            let colorClass = "text-zinc-300";
            if (isError) colorClass = "text-amber-400";
            if (isSuccess) colorClass = "text-emerald-400 font-semibold";
            if (isHitl) colorClass = "text-violet-400";
            if (isNode) colorClass = "text-[#06B6D4]";

            return (
              <div
                key={idx}
                className={`rounded border border-white/5 bg-black/40 px-2.5 py-1.5 ${colorClass}`}
              >
                {log}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};


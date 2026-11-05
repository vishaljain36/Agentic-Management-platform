import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Bot, ShieldAlert, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentNodeData } from "@/store/use-canvas-store";

const AgentNodeComponent: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeData = data as unknown as AgentNodeData;
  const status = nodeData.status || "idle";

  const statusConfig = {
    idle: {
      border: "border-white/10 hover:border-[#8B5CF6]/50",
      glow: "shadow-none",
      badge: "bg-zinc-800 text-zinc-400 border-zinc-700",
      icon: <Bot className="h-4 w-4 text-zinc-400" />,
      text: "IDLE",
    },
    running: {
      border: "border-[#8B5CF6] shadow-neon-violet",
      glow: "shadow-neon-violet",
      badge: "bg-[#8B5CF6]/20 text-[#8B5CF6] border-[#8B5CF6]/40",
      icon: <Loader2 className="h-4 w-4 animate-spin text-[#8B5CF6]" />,
      text: "ACTIVE",
    },
    waiting: {
      border: "border-[#F59E0B] shadow-neon-amber animate-pulse-glow",
      glow: "shadow-neon-amber",
      badge: "bg-[#F59E0B]/20 text-[#F59E0B] border-[#F59E0B]/40",
      icon: <ShieldAlert className="h-4 w-4 text-[#F59E0B]" />,
      text: "HITL PAUSED",
    },
    completed: {
      border: "border-[#10B981] shadow-[0_0_15px_-2px_rgba(16,185,129,0.35)]",
      glow: "",
      badge: "bg-[#10B981]/20 text-[#10B981] border-[#10B981]/40",
      icon: <CheckCircle2 className="h-4 w-4 text-[#10B981]" />,
      text: "COMPLETED",
    },
    error: {
      border: "border-red-500 shadow-[0_0_15px_-2px_rgba(239,68,68,0.4)]",
      glow: "",
      badge: "bg-red-500/20 text-red-400 border-red-500/40",
      icon: <Bot className="h-4 w-4 text-red-400" />,
      text: "ERROR",
    },
  }[status];

  return (
    <div
      className={cn(
        "group relative min-w-[220px] rounded-xl border bg-[#0F172A]/85 p-3.5 backdrop-blur-cyber transition-all duration-300",
        statusConfig.border,
        selected && "ring-2 ring-[#8B5CF6]"
      )}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!h-3 !w-3 !rounded-full !border-2 !border-[#0F172A] !bg-[#8B5CF6]"
      />

      {/* Header */}
      <div className="flex items-center justify-between gap-2 border-b border-white/5 pb-2">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/5 border border-white/10">
            {statusConfig.icon}
          </div>
          <div>
            <h4 className="text-xs font-semibold tracking-wider text-zinc-100">
              {nodeData.label}
            </h4>
            <span className="text-[10px] text-zinc-400">{nodeData.model}</span>
          </div>
        </div>
        <span
          className={cn(
            "rounded border px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-wider",
            statusConfig.badge
          )}
        >
          {statusConfig.text}
        </span>
      </div>

      {/* Description / Role */}
      <div className="mt-2 text-[11px] text-zinc-300">
        {nodeData.role}
      </div>

      {/* Bound Tools list */}
      {nodeData.tools && nodeData.tools.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1">
          {nodeData.tools.map((tool) => (
            <span
              key={tool}
              className="inline-flex items-center gap-1 rounded bg-[#030712]/60 px-1.5 py-0.5 text-[9px] font-mono text-[#06B6D4] border border-[#06B6D4]/20"
            >
              <Sparkles className="h-2 w-2" />
              {tool}
            </span>
          ))}
        </div>
      )}

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!h-3 !w-3 !rounded-full !border-2 !border-[#0F172A] !bg-[#06B6D4]"
      />
    </div>
  );
};

export const AgentNode = memo(AgentNodeComponent);


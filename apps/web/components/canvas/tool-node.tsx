import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Terminal, Database, Search, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ToolNodeData } from "@/store/use-canvas-store";

const ToolNodeComponent: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeData = data as unknown as ToolNodeData;
  const category = nodeData.category || "search";

  const categoryConfig = {
    search: {
      icon: <Search className="h-3.5 w-3.5 text-[#06B6D4]" />,
      border: "border-[#06B6D4]/30 hover:border-[#06B6D4]/70",
      accent: "text-[#06B6D4]",
    },
    code: {
      icon: <Terminal className="h-3.5 w-3.5 text-[#10B981]" />,
      border: "border-[#10B981]/30 hover:border-[#10B981]/70",
      accent: "text-[#10B981]",
    },
    database: {
      icon: <Database className="h-3.5 w-3.5 text-[#8B5CF6]" />,
      border: "border-[#8B5CF6]/30 hover:border-[#8B5CF6]/70",
      accent: "text-[#8B5CF6]",
    },
    retrieval: {
      icon: <Cpu className="h-3.5 w-3.5 text-[#06B6D4]" />,
      border: "border-[#06B6D4]/30 hover:border-[#06B6D4]/70",
      accent: "text-[#06B6D4]",
    },
  }[category];

  return (
    <div
      className={cn(
        "group relative min-w-[180px] rounded-lg border bg-[#030712]/80 px-3 py-2.5 backdrop-blur-cyber transition-all duration-200",
        categoryConfig.border,
        selected && "ring-2 ring-[#06B6D4]"
      )}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !rounded-full !border !border-[#030712] !bg-[#06B6D4]"
      />

      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded bg-white/5 border border-white/10">
          {categoryConfig.icon}
        </div>
        <div>
          <h5 className="text-[11px] font-medium tracking-wide text-zinc-200">
            {nodeData.label}
          </h5>
          <span className={cn("text-[9px] font-mono uppercase", categoryConfig.accent)}>
            {category}
          </span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !rounded-full !border !border-[#030712] !bg-[#10B981]"
      />
    </div>
  );
};

export const ToolNode = memo(ToolNodeComponent);


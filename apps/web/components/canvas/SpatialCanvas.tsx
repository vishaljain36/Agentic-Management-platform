"use client";

import React, { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  ReactFlowProvider,
} from "@xyflow/react";

import { useCanvasStore } from "@/store/use-canvas-store";
import { useAgentStore } from "@/store/use-agent-store";

import { AgentNode } from "@/components/canvas/agent-node";
import { ToolNode } from "@/components/canvas/tool-node";
import { EdgePulse } from "@/components/canvas/edge-pulse";
import { HitlModal } from "@/components/canvas/hitl-modal";
import { AlertTriangle } from "lucide-react";

export interface SpatialCanvasProps {
  className?: string;
  onNodeClick?: (event: React.MouseEvent, node: any) => void;
}

export const SpatialCanvasInner: React.FC<SpatialCanvasProps> = ({
  className = "",
  onNodeClick,
}) => {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    hasCycle,
    cycleWarning,
  } = useCanvasStore();

  const { activeNode, status } = useAgentStore();

  const nodeTypes = useMemo(
    () => ({
      agentNode: AgentNode,
      toolNode: ToolNode,
    }),
    []
  );

  const edgeTypes = useMemo(
    () => ({
      edgePulse: EdgePulse,
    }),
    []
  );

  const displayNodes = useMemo(() => {
    return nodes.map((node) => {
      let nodeStatus = "idle";
      if (status === "RUNNING") {
        if (node.id === activeNode || node.data?.label === activeNode) {
          nodeStatus = "running";
        }
      }
      return {
        ...node,
        data: {
          ...node.data,
          status: node.data?.status || nodeStatus,
        },
      };
    });
  }, [nodes, activeNode, status]);

  return (
    <div
      data-testid="spatial-canvas"
      className={`relative h-full w-full overflow-hidden bg-void ${className}`}
    >
      {/* Non-DAG cycle warning badge */}
      {hasCycle && (
        <div
          data-testid="cycle-warning-badge"
          className="absolute top-4 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 rounded-full border border-red-500/50 bg-red-950/80 px-4 py-1.5 text-xs font-semibold text-red-300 shadow-neon-amber backdrop-blur-md"
        >
          <AlertTriangle className="h-4 w-4 text-red-400" />
          <span>{cycleWarning || "Non-DAG cycle detected"}</span>
        </div>
      )}

      <ReactFlow
        nodes={displayNodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        colorMode="dark"
        proOptions={{ hideAttribution: true }}
        className="cyber-flow"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1.5}
          color="#1e1b4b"
          className="opacity-70"
        />
        <Controls
          className="!border-white/10 !bg-[#0B0F19]/80 !fill-white text-white backdrop-blur-cyber"
          showInteractive={false}
        />
        <MiniMap
          nodeStrokeWidth={3}
          zoomable
          pannable
          className="!border-white/10 !bg-[#030712]/90 !rounded-xl overflow-hidden backdrop-blur-cyber shadow-2xl"
          maskColor="rgba(3, 7, 18, 0.75)"
          nodeColor={(n) => {
            if (n.type === "agentNode") return "#8B5CF6";
            if (n.type === "toolNode") return "#06B6D4";
            return "#64748b";
          }}
        />
      </ReactFlow>

      <HitlModal />
    </div>
  );
};

export const SpatialCanvas: React.FC<SpatialCanvasProps> = (props) => (
  <ReactFlowProvider>
    <SpatialCanvasInner {...props} />
  </ReactFlowProvider>
);


"use client";

import React, { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
} from "@xyflow/react";

import { useCanvasStore } from "@/store/use-canvas-store";
import { useAgentStore } from "@/store/use-agent-store";

import { AgentNode } from "@/components/canvas/agent-node";
import { ToolNode } from "@/components/canvas/tool-node";
import { EdgePulse } from "@/components/canvas/edge-pulse";
import { HitlModal } from "@/components/canvas/hitl-modal";
import { ThoughtTree } from "@/components/chat/thought-tree";
import { StreamChat } from "@/components/chat/stream-chat";
import { SandboxTerminal } from "@/components/sandbox/terminal";
import { Button } from "@/components/ui/button";

import { Bot, Plus, Terminal, Database, Sparkles } from "lucide-react";

export default function WorkspaceCanvasPage() {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addAgentNode,
  } = useCanvasStore();

  const { activeNode, status } = useAgentStore();

  // Register custom node & edge types
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

  // Sync active node status into React Flow nodes
  const displayNodes = useMemo(() => {
    return nodes.map((node) => {
      let nodeStatus = "idle";
      if (status === "RUNNING") {
        if (node.id === activeNode || node.data?.label === activeNode) {
          nodeStatus = "running";
        }
      } else if (status === "WAITING_FOR_HUMAN") {
        if (node.id === "human_approval" || node.id === activeNode) {
          nodeStatus = "waiting";
        }
      } else if (status === "COMPLETED") {
        nodeStatus = "completed";
      }

      return {
        ...node,
        data: {
          ...node.data,
          status: nodeStatus,
        },
      };
    });
  }, [nodes, activeNode, status]);

  return (
    <div className="relative flex h-full w-full overflow-hidden bg-void">
      {/* 1. LEFT PANEL: Agent Swarm Navigation & Insertion */}
      <aside className="z-10 flex w-64 shrink-0 flex-col border-r border-white/10 bg-[#0B0F19]/80 p-3.5 backdrop-blur-cyber">
        <div className="mb-3 flex items-center justify-between border-b border-white/5 pb-2">
          <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-300">
            <Bot className="h-4 w-4 text-[#8B5CF6]" />
            Agent Swarm Nodes
          </span>
        </div>

        <div className="flex-1 space-y-2 overflow-y-auto pr-1">
          <div className="rounded-lg border border-white/5 bg-black/40 p-2.5 hover:border-[#8B5CF6]/30 transition-all">
            <div className="flex items-center justify-between text-xs font-medium text-zinc-200">
              <span>Researcher Agent</span>
              <span className="rounded bg-[#8B5CF6]/20 px-1 text-[9px] text-[#8B5CF6]">Active</span>
            </div>
            <p className="mt-1 text-[11px] text-zinc-400">Web Search & Vector Index Querying</p>
          </div>

          <div className="rounded-lg border border-white/5 bg-black/40 p-2.5 hover:border-[#8B5CF6]/30 transition-all">
            <div className="flex items-center justify-between text-xs font-medium text-zinc-200">
              <span>Evaluator Agent</span>
              <span className="rounded bg-[#06B6D4]/20 px-1 text-[9px] text-[#06B6D4]">HITL Gate</span>
            </div>
            <p className="mt-1 text-[11px] text-zinc-400">AST parsing and mutation sandboxing</p>
          </div>

          <div className="rounded-lg border border-white/5 bg-black/40 p-2.5 hover:border-[#8B5CF6]/30 transition-all">
            <div className="flex items-center justify-between text-xs font-medium text-zinc-200">
              <span>HITL Checkpoint</span>
              <span className="rounded bg-[#F59E0B]/20 px-1 text-[9px] text-[#F59E0B]">Review</span>
            </div>
            <p className="mt-1 text-[11px] text-zinc-400">Administrator consent gatekeeper</p>
          </div>

          <div className="rounded-lg border border-white/5 bg-black/40 p-2.5 hover:border-[#8B5CF6]/30 transition-all">
            <div className="flex items-center justify-between text-xs font-medium text-zinc-200">
              <span>Final Writer</span>
              <span className="rounded bg-[#10B981]/20 px-1 text-[9px] text-[#10B981]">Sink</span>
            </div>
            <p className="mt-1 text-[11px] text-zinc-400">Synthesis, markdown, telemetry report</p>
          </div>
        </div>

        {/* Add custom node trigger */}
        <div className="mt-3 border-t border-white/5 pt-3">
          <Button
            size="sm"
            variant="secondary"
            className="w-full flex items-center justify-center gap-1.5 text-xs"
            onClick={() => addAgentNode("Custom Specialist", "Domain Expert Analyzer")}
          >
            <Plus className="h-3.5 w-3.5" />
            Add Custom Agent
          </Button>
        </div>
      </aside>

      {/* 2. CENTER: Interactive React Flow Spatial Canvas */}
      <main className="relative flex-1 h-full w-full">
        <ReactFlow
          nodes={displayNodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
          colorMode="dark"
          defaultEdgeOptions={{ type: "edgePulse" }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={20}
            size={1.5}
            color="rgba(255, 255, 255, 0.08)"
          />
          <Controls className="!bottom-4 !left-4" />
          <MiniMap
            className="!bottom-4 !right-4 !w-36 !h-24"
            nodeColor={(n) => (n.type === "agentNode" ? "#8B5CF6" : "#06B6D4")}
          />
        </ReactFlow>

        {/* Bottom Floating Telemetry Panel */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 w-[92%] max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-3 h-52">
          <StreamChat />
          <ThoughtTree />
        </div>
      </main>

      {/* 3. RIGHT PANEL: Sandbox Terminal & Knowledge Context */}
      <aside className="z-10 flex w-80 shrink-0 flex-col border-l border-white/10 bg-[#0B0F19]/80 p-3.5 backdrop-blur-cyber">
        <SandboxTerminal />
      </aside>

      {/* 4. Human-In-The-Loop Approval Modal */}
      <HitlModal />
    </div>
  );
}

